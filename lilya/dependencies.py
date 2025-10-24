from __future__ import annotations

import contextlib
import inspect
import sys
from collections.abc import Callable, Coroutine, Sequence
from functools import cached_property, lru_cache, wraps
from types import GeneratorType
from typing import Any, TypeVar, cast

from lilya._internal._scopes import scope_manager
from lilya.compat import is_async_callable, run_sync
from lilya.enums import Scope, SignatureDefault
from lilya.requests import Request
from lilya.websockets import WebSocket

T = TypeVar("T")

SIGNATURE_TO_LIST = SignatureDefault.to_list()

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@lru_cache(maxsize=1024)
def wrap_dependency(
    dependency: Callable[..., Any] | Any,
    *args: Any,
    use_cache: bool = False,
    **kwargs: Any,
) -> Provide:
    """
    Wraps a dependency factory callable or a constant value into a `Provide` instance.

    If the input is already a `Provide` instance, it is returned as is. If the input
    is a non-callable value, it is wrapped in a lambda to make it callable.

    Args:
        dependency: The dependency factory function or the literal value to provide.
        use_cache: Whether to cache the resolved result for the lifetime of the call.
        *args: Positional arguments to be passed to the factory function.
        **kwargs: Keyword arguments to be passed to the factory function.

    Returns:
        A `Provide` instance ready for dependency resolution.
    """
    if not isinstance(dependency, Provide):
        if not callable(dependency):
            return Provide(lambda: dependency, *args, use_cache=use_cache, **kwargs)
        return Provide(dependency, *args, use_cache=use_cache, **kwargs)
    return dependency


class Provide:
    """
    A request-aware dependency marker and wrapper.

    When used in a handler's signature (e.g., `user: User = Provide(get_user)`), this
    class manages:
    1. Inspection and recursive resolution of nested dependencies.
    2. Caching of the resolved result (`use_cache`).
    3. Lifespan control using `Scope.REQUEST`, `Scope.APP`, or `Scope.GLOBAL`.
    4. Cleanup registration for generator-based dependencies.
    """

    def __init__(
        self,
        dependency: Callable[..., Any],
        *args: Any,
        use_cache: bool = False,
        scope: Scope | str | None = Scope.REQUEST,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the dependency provider.

        Args:
            dependency: The callable factory (function or class) that creates the dependency.
            use_cache: If True, the result is cached for the duration of the top-level resolution call.
            scope: Defines the lifespan of the dependency instance.
                   Can be 'request', 'app', or 'global', or their corresponding `Scope` enum members.
            *args: Positional arguments to pass to the dependency callable.
            **kwargs: Keyword arguments to pass to the dependency callable.

        Raises:
            ValueError: If an invalid scope string is provided.
        """
        self.dependency: Callable[..., Any] = dependency
        self.provided_args: tuple[Any, ...] = args
        self.provided_kwargs: dict[str, Any] = kwargs
        self.use_cache: bool = use_cache

        # Normalize scope from string to Enum
        if isinstance(scope, str):
            try:
                scope = Scope[scope.upper()]
            except KeyError as exc:
                raise ValueError(
                    f"Invalid scope '{scope}'. Use one of: {[s.name for s in Scope]}"
                ) from exc

        self.scope: Scope | None = scope
        self._cache: Any = None
        self._resolved: bool = False
        self.__dependency_signature__: inspect.Signature | None = None

    @cached_property
    def __signature__(self) -> inspect.Signature:
        """
        Returns the signature of the dependency function, caching the result.
        This is used internally to introspect the parameters of the dependency.
        """
        if self.__dependency_signature__ is None:
            self.__dependency_signature__ = inspect.signature(self.dependency)
        return self.__dependency_signature__

    async def resolve(
        self,
        request: Request,
        dependencies_map: dict[str, Self | Any],
    ) -> Any:
        """
        Resolves the dependency, handling scoping and caching.

        If the scope is APP or GLOBAL, it delegates to the `scope_manager` to retrieve
        a cached instance or create a new one via `_resolve_internal`.

        Args:
            request: The current HTTP Request object, used for cleanup registration and context injection.
            dependencies_map: A map of dependency names to their respective `Provide` instances or values.

        Returns:
            The fully resolved dependency instance.
        """
        # Return cached value if already resolved for this resolution call
        if self.use_cache and self._resolved:
            return self._cache

        if self.scope in (Scope.APP, Scope.GLOBAL):

            async def _factory() -> Any:
                # Delegate to internal resolution logic
                return await self._resolve_internal(request, dependencies_map)

            if self.scope == Scope.APP:
                app = getattr(request, "app", None)
                attr_name = f"__lilya_app_depkey_{id(self.dependency)}"

                if app is not None:
                    # real Lilya app — reuse per-app wrapper
                    dep_key = getattr(app, attr_name, None)
                    if dep_key is None:

                        def _app_scoped_key(*args: Any, **kwargs: Any) -> Any:
                            return self.dependency(*args, **kwargs)

                        setattr(app, attr_name, _app_scoped_key)
                        dep_key = _app_scoped_key
                else:
                    # fallback for no app, stable per Provide key
                    if not hasattr(self, "_app_scope_key"):

                        def _app_scoped_key(*args: Any, **kwargs: Any) -> Any:
                            return self.dependency(*args, **kwargs)

                        self._app_scope_key = _app_scoped_key
                    dep_key = self._app_scope_key
            else:
                dep_key = self.dependency

            # retrieve or create from scope_manager
            return await scope_manager.get_or_create(
                self.scope,
                dep_key,  # callable identity
                _factory,
            )

        # For Scope.REQUEST, call internal resolution directly
        return await self._resolve_internal(request, dependencies_map)

    async def _resolve_internal(
        self,
        request: Request,
        dependencies_map: dict[str, Self | Any],
    ) -> Any:
        """
        Internal dependency resolution logic, executed when creating a new instance
        (used by resolve() and scope_manager).
        """
        # Try to update provided_kwargs with request data if relevant
        if self.__signature__.parameters:
            try:
                # Attempt to parse request body data (JSON)
                json_data = cast(dict[str, Any], await request.data()) or {}
            except Exception:
                json_data = {}

            param_names = self.__signature__.parameters.keys()

            # Map body data to unprovided parameters
            for key, value in json_data.items():
                if key in param_names and key not in dependencies_map:
                    self.provided_kwargs[key] = value

        # Direct Call Optimization
        # If explicit arguments were provided or dependency is a class, call directly,
        # bypassing nested dependency resolution (since inspection isn't needed).
        if self.provided_args or self.provided_kwargs or inspect.isclass(self.dependency):
            if inspect.iscoroutinefunction(self.dependency) or is_async_callable(self.dependency):
                result = await self.dependency(*self.provided_args, **self.provided_kwargs)
            else:
                result = self.dependency(*self.provided_args, **self.provided_kwargs)

            if self.use_cache:
                self._cache = result
                self._resolved = True
            return result

        # Nested Dependency Resolution ---
        sig = inspect.signature(self.dependency)
        kwargs: dict[str, Any] = {}

        # Resolve each parameter of this dependency function
        for name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            # If default is a marker (Resolve, Security), resolve the whole tree
            if isinstance(param.default, (Resolve, Security)):
                # Note: This recursive call logic seems to resolve all dependencies for the *parent* function again
                kwargs[name] = await async_resolve_dependencies(
                    request=request,
                    func=self.dependency,
                )
                continue

            if name in dependencies_map:
                dep = dependencies_map[name]

                if isinstance(dep, Provide):
                    # Recursive resolution for nested Provide instances
                    kwargs[name] = await dep.resolve(request, dependencies_map)
                elif hasattr(dep, "resolve"):
                    # Resolve generic dependency objects (like Security or custom types)
                    try:
                        result = await dep.resolve(dependencies_map)
                    except TypeError:
                        result = await dep.resolve(request, dependencies_map)
                    kwargs[name] = result
                elif callable(dep):
                    # Standard callable/factory resolution
                    dep_sig = inspect.signature(dep)
                    dep_params = dep_sig.parameters

                    # If dependency expects exactly one positional parameter, inject request
                    if len(dep_params) == 1:
                        param_obj = next(iter(dep_params.values()))
                        if param_obj.kind in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        ):
                            result = dep(request)
                        else:
                            result = dep()
                    else:
                        result = dep()

                    if inspect.isawaitable(result):
                        result = await result
                    kwargs[name] = result
                else:
                    # Direct value injection
                    kwargs[name] = dep

        call_kwargs = {**self.provided_kwargs, **kwargs}

        dep_sig = inspect.signature(self.dependency)
        dep_params = dep_sig.parameters

        # Automatic Request/Connection Injection Logic
        should_inject_request = False

        if len(dep_params) > 0:
            # Case 1: explicit "request" param
            if "request" in dep_params and "request" not in call_kwargs:
                should_inject_request = True
            # Case 2: exactly one positional argument, no defaults, and no args/kwargs provided
            elif (
                len(dep_params) == 1
                and next(iter(dep_params.values())).kind
                in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                and next(iter(dep_params.values())).default is inspect._empty
                and not self.provided_args
                and not self.provided_kwargs
                and next(iter(dep_params.keys())) not in call_kwargs
            ):
                should_inject_request = True

        if should_inject_request:
            # Get the name of the first/target parameter
            param_name = next(iter(dep_params.keys()))
            call_kwargs[param_name] = request

        # Final Dependency Call
        if inspect.iscoroutinefunction(self.dependency) or is_async_callable(self.dependency):
            result = await self.dependency(*self.provided_args, **call_kwargs)
        else:
            result = self.dependency(*self.provided_args, **call_kwargs)

        if self.use_cache:
            self._cache = result
            self._resolved = True

        # Generator/Coroutine Cleanup
        if isinstance(result, GeneratorType):
            try:
                # Get the yielded value
                value = next(result)
            except StopIteration:
                return None
            # Register the generator's close() method for cleanup after the request
            request.add_cleanup(result.close)
            return value
        if inspect.isasyncgen(result):
            try:
                # Get the yielded value
                value = await result.__anext__()
            except StopAsyncIteration:
                return None
            # Register the async generator's aclose() method for cleanup after the request
            request.add_cleanup(result.aclose)
            return value

        return result


class Provides:
    """
    Parameter-default marker. Use this in your handler signature to
    signal "please take my `dependencies['foo']` and inject it here."

    This is primarily used for injecting dependencies registered in a router or
    handler's `dependencies` map based on the parameter name.
    """

    def __init__(self) -> None:
        """
        Initializes the marker. It holds no state.
        """
        ...


class Resolve(Provide):
    """
    Parameter default marker. Use this in your handler signature to
    signal "please resolve this dependency and inject it here."

    This marker is often used to signal that the dependency function itself
    should have *its own* dependencies resolved recursively before being called.
    """

    def __repr__(self) -> str:
        """
        Custom representation for debugging/introspection.
        """
        return "Resolve()"


class Security(Provide):
    """
    Parameter default marker. Used to signal that a security dependency must be
    resolved and injected here.

    Security dependencies are often special because they may require access to
    scopes or explicit request data for authentication/authorization checks.
    """

    def __init__(
        self,
        dependency: Callable[..., Any],
        *args: Any,
        scopes: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the Security dependency.

        Args:
            dependency: The security dependency function (e.g., an authentication scheme).
            scopes: A list of required scopes for authorization, often used by the caller
                    to enforce policy.
            *args: Positional arguments for the dependency.
            **kwargs: Keyword arguments for the dependency.
        """
        # Call Provide's init with the dependency
        super().__init__(dependency=dependency, *args, **kwargs)
        self.scopes: Sequence[str] = scopes or []


async def async_resolve_dependencies(
    request: Request | WebSocket,
    func: Callable[..., Any],
    overrides: dict[str, Any] | None = None,
) -> Any:
    """
    Resolves dependencies for an **asynchronous** function by inspecting its signature.

    This utility is used internally by `Resolve` and `Security` markers to handle
    nested resolution without being limited to `Provide` instances.

    Args:
        request: The current connection object (Request or WebSocket).
        func: The target function whose dependencies need to be resolved.
        overrides: A dictionary of dependency overrides (function identity or name -> replacement).

    Returns:
        The result of the target function with its dependencies resolved.
    """
    if overrides is None:
        overrides = {}

    kwargs: dict[str, Any] = {}

    signature = inspect.signature(func)

    for name, param in signature.parameters.items():
        # Resolve Security and Resolve markers recursively
        if isinstance(param.default, Security):
            # Security dependencies often receive the request directly
            kwargs[name] = await param.default.dependency(request)
        if isinstance(param.default, Resolve):
            dep_func = param.default.dependency
            dep_func = overrides.get(dep_func, dep_func)  # type: ignore

            # Recursive call if the dependency is async
            if inspect.iscoroutinefunction(dep_func):
                resolved = await async_resolve_dependencies(
                    request=request,
                    func=dep_func,
                    overrides=overrides,
                )
            else:
                # If dependency is sync, run sync resolution
                resolved = (
                    resolve_dependencies(request, dep_func, overrides)
                    if callable(dep_func)
                    else dep_func
                )
            kwargs[name] = resolved

    # Final call to the target function
    if inspect.iscoroutinefunction(func):
        result = await func(**kwargs)
    else:
        result = func(**kwargs)

    # Handle generator/coroutine cleanup for the *result* of this function
    if isinstance(result, GeneratorType):
        try:
            value = next(result)
        except StopIteration:
            return None
        request.add_cleanup(result.close)
        return value

    if inspect.isasyncgen(result):
        try:
            value = await result.__anext__()
        except StopAsyncIteration:
            return None
        request.add_cleanup(result.aclose)
        return value

    return result


def resolve_dependencies(
    request: Request | WebSocket,
    func: Any,
    overrides: dict[str, Any] | None = None,
) -> Any:
    """
    Resolves the dependencies for a **synchronous** function by running the
    asynchronous resolution logic synchronously.

    This function is primarily used internally when a synchronous dependency calls
    for resolution of a nested tree.

    Args:
        request: The current connection object (Request or WebSocket).
        func: The synchronous function for which dependencies need to be resolved.
        overrides: A dictionary of dependency overrides.

    Returns:
        The result of running the asynchronous dependency resolution function synchronously.

    Raises:
        ValueError: If the provided function is asynchronous (must be handled by `async_resolve_dependencies`).
    """
    if overrides is None:
        overrides = {}
    if inspect.iscoroutinefunction(func):
        raise ValueError("Function is async. Use resolve_dependencies_async instead.")

    # Run the core async resolution logic synchronously
    return run_sync(async_resolve_dependencies(request, func, overrides))


class PureScope:
    """
    Async context manager for managing cleanup of resources in a request-less scope
    (e.g., background tasks, non-ASGI testing environments).

    It mimics the cleanup mechanism of a request/websocket object.

    Usage:
        async with PureScope() as scope:
            # Inject resources that use this scope for cleanup
            ...
        # Resources are cleaned up upon exiting the 'async with' block.
    """

    def __init__(self) -> None:
        """
        Initializes the scope with an empty list of cleanup functions.
        """
        self._cleanups: list[
            tuple[Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]], bool]
        ] = []

    def add_cleanup(
        self, fn: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]], is_async: bool
    ) -> None:
        """
        Register a cleanup function to be called when the scope is closed.

        Args:
            fn: The cleanup function (sync or async) to register.
            is_async: True if `fn` is an asynchronous function (coroutine).
        """
        self._cleanups.append((fn, is_async))

    async def aclose(self) -> None:
        """
        Call all registered cleanup functions in Last-In, First-Out (LIFO) order.

        Any exceptions raised by cleanup functions are suppressed to ensure all
        cleanup routines are attempted.
        """
        while self._cleanups:
            fn, is_async = self._cleanups.pop()
            try:
                if is_async:
                    await fn()
                else:
                    fn()
            except Exception:  # noqa: E722
                # Suppress exceptions during cleanup
                ...

    async def __aenter__(self) -> PureScope:
        """
        Enter the async context manager.
        """
        return self

    async def __aexit__(self, et: Any, ev: Any, tb: Any) -> None:
        """
        Exit the async context manager and perform cleanup by calling `aclose`.
        """
        await self.aclose()


def _constant(value: Any) -> Callable[[], Any]:
    """
    Wrap a non-callable value in a zero-argument function.

    This is used internally by `Depends` when the dependency provided is a static
    value, ensuring it adheres to the callable dependency contract.
    """

    def return_value(_v: Any = value) -> Any:
        """
        Return the constant value.
        """
        return _v

    # Rename the function for clearer introspection
    return_value.__name__ = "constant"
    return return_value


class _Depends:
    """
    Parameter default marker and dependency wrapper for **request-agnostic** resolution.

    This class enables dependency injection in contexts where a Request object is
    not available (e.g., service layers, background tasks, unit tests).

    Lifespan management (Scope.APP, Scope.GLOBAL) relies on the shared `scope_manager`.

    Usage in signatures:
        def handler(repo = Depends(get_repo)): ...
    """

    def __init__(
        self,
        dependency: Callable[..., Any] | Any,
        *args: Any,
        use_cache: bool = False,
        scope: Scope | str | None = Scope.REQUEST,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the request-agnostic dependency provider.

        The `Request` object is not injected or resolved here. Lifespan is managed
        via the `scope` parameter.

        Args:
            dependency: The dependency factory function or the static value.
            use_cache: If True, caches the result for the lifetime of the call/scope.
            scope: Defines the lifespan of the dependency instance.
            *args: Positional arguments to pass to the factory function.
            **kwargs: Keyword arguments to pass to the factory function.
        """
        if not isinstance(dependency, _Depends) and not callable(dependency):
            # Wrap static value in a constant function
            dependency = _constant(dependency)
        self.dependency: Callable[..., Any] = dependency  # type: ignore
        self.provided_args: tuple[Any, ...] = args
        self.provided_kwargs: dict[str, Any] = kwargs
        self.use_cache: bool = use_cache

        # Normalize scope from string to Enum
        if isinstance(scope, str):
            try:
                scope = Scope[scope.upper()]
            except KeyError as exc:
                raise ValueError(
                    f"Invalid scope '{scope}'. Use one of: {[s.name for s in Scope]}"
                ) from exc

        self.scope: Scope | None = scope
        self._cache: Any = None
        self._resolved: bool = False
        self.__dependency_signature__: inspect.Signature | None = None

    def __repr__(self) -> str:
        """
        Custom representation for debugging/introspection.
        """
        name = getattr(self.dependency, "__name__", type(self.dependency).__name__)
        return f"Depends({name})"

    @cached_property
    def __signature__(self) -> inspect.Signature:
        """
        Returns the signature of the dependency function, caching the result.
        """
        if self.__dependency_signature__ is None:
            # Type ignore is used because dependency is guaranteed callable or wrapped by _constant
            self.__dependency_signature__ = inspect.signature(self.dependency)
        return self.__dependency_signature__

    async def resolve(
        self,
        dependencies_map: dict[str, Any] | None = None,
        overrides: dict[Any, Any] | None = None,
        scope: PureScope | None = None,
    ) -> Any:
        """
        Resolves the dependency tree without requiring a Request/WebSocket object.

        Args:
            dependencies_map: A map of dependency names to nested `Depends` instances or static values.
            overrides: A map to replace a dependency callable with another callable or static value.
            scope: A `PureScope` instance used for cleanup registration of generator resources.

        Returns:
            The fully resolved dependency instance.
        """
        if self.use_cache and self._resolved:
            return self._cache

        dependencies_map = dependencies_map or {}
        overrides = overrides or {}

        if self.scope in (Scope.APP, Scope.GLOBAL):

            async def _factory() -> Any:
                # the actual internal resolution logic below
                return await self._resolve_internal(dependencies_map, overrides, scope)

            # Determine the callable identity for scope_manager caching
            if isinstance(self.dependency, _Depends):

                def dep_callable() -> Any:  # type: ignore
                    return self.dependency

            elif callable(self.dependency):
                dep_callable = self.dependency
            else:
                dep_callable = _constant(self.dependency)  # type: ignore

            return await scope_manager.get_or_create(
                self.scope,  # Safe cast due to type check in __init__
                dep_callable,
                _factory,
            )

        # For Scope.REQUEST (which is treated as per-call here), resolve internally
        return await self._resolve_internal(dependencies_map, overrides, scope)

    async def _resolve_internal(
        self,
        dependencies_map: dict[str, Any],
        overrides: dict[Any, Any],
        scope: PureScope | None,
    ) -> Any:
        """
        Internal resolution logic for the request-agnostic `Depends` class.
        """
        # If args/kwargs explicitly provided or this is a class, call directly.
        if self.provided_args or self.provided_kwargs or inspect.isclass(self.dependency):
            dep_callable = overrides.get(self.dependency, self.dependency)

            result = await _maybe_call_async(
                dep_callable, *self.provided_args, **self.provided_kwargs
            )
            result = await _handle_generators_requestless(result, scope=scope)

            if self.use_cache:
                self._cache, self._resolved = result, True
            return result

        # Otherwise, introspect the dependency function and build kwargs.
        signature = inspect.signature(self.dependency)
        kwargs: dict[str, Any] = {}

        for name, param in signature.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            # Nested requestless Depends marker in the callee signature
            if isinstance(param.default, _Depends):
                kwargs[name] = await param.default.resolve(
                    dependencies_map, overrides, scope=scope
                )
                continue

            # Name-based resolution via dependencies_map
            if name in dependencies_map:
                nested = dependencies_map[name]
                if isinstance(nested, _Depends):
                    kwargs[name] = await nested.resolve(dependencies_map, overrides, scope=scope)
                else:
                    # value or callable
                    if callable(nested):
                        kwargs[name] = await _maybe_call_async(nested)
                    else:
                        kwargs[name] = nested
                continue

            # Fall back to default value if provided
            if param.default is not inspect._empty:
                # We respect the default literally (pass the callable object, not its result)
                kwargs[name] = param.default
                continue

            # No way to resolve
            raise RuntimeError(
                f"Could not resolve parameter '{name}' for dependency "
                f"'{getattr(self.dependency, '__name__', self.dependency)}' "
                "(no request available and no mapping/default provided)"
            )

        dep_callable = overrides.get(self.dependency, self.dependency)

        result = await _maybe_call_async(
            dep_callable, *self.provided_args, **{**self.provided_kwargs, **kwargs}
        )
        result = await _handle_generators_requestless(result, scope=scope)

        # Cache if requested
        if self.use_cache:
            self._cache, self._resolved = result, True

        return result


def Depends(
    dependency: Callable[..., Any] | Any,
    *args: Any,
    use_cache: bool = False,
    **kwargs: Any,
) -> _Depends:
    """
    Factory function for the request-less `_Depends` marker.

    This function attempts to cache the constructed `_Depends` instance based on its
    arguments for performance, falling back to a direct `_Depends` creation if the
    arguments are unhashable.

    Args:
        dependency: The dependency factory or static value.
        *args: Positional arguments for the dependency.
        use_cache: If True, the result of the dependency resolution will be cached.
        **kwargs: Keyword arguments for the dependency.

    Returns:
        A cached or newly created `_Depends` instance.
    """
    if not callable(dependency):
        # Wrap non-callable values in a constant function
        return _Depends(_constant(dependency), *args, use_cache=use_cache, **kwargs)

    try:
        # Create a hashable key for caching the Depends instance itself
        key: tuple[
            Callable[..., Any],
            tuple[Any, ...],
            frozenset[tuple[str, Any]],
            bool,
        ] = (
            dependency,
            tuple(args),
            frozenset(kwargs.items()),
            use_cache,
        )
        hash(key)  # Test hashability
    except TypeError:
        # Cannot cache the Depends instance due to unhashable args/kwargs
        return _Depends(dependency, *args, use_cache=use_cache, **kwargs)

    # Return cached instance if key is hashable
    return _depends_cached(key)


@lru_cache(maxsize=1024)
def _depends_cached(
    key: tuple[
        Callable[..., Any],
        tuple[Any, ...],
        frozenset[tuple[str, Any]],
        bool,
    ],
) -> _Depends:
    """
    Internal cached factory for Depends.
    """
    dependency, args, kw_items, use_cache = key
    return _Depends(dependency, *args, use_cache=use_cache, **dict(kw_items))


async def _maybe_call_async(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """
    Calls a function that may be synchronous or asynchronous, awaiting the result
    if necessary.

    Args:
        fn: The function/callable to execute.
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        The result of the function call, awaited if it was a coroutine.
    """
    if inspect.iscoroutinefunction(fn) or is_async_callable(fn):
        return await fn(*args, **kwargs)
    return fn(*args, **kwargs)


async def _handle_generators_requestless(result: Any, scope: PureScope | None = None) -> Any:
    """
    Handles cleanup for generator and async generator dependencies in a request-less
    context.

    Strategy:
    - If a `PureScope` is provided, the generator's cleanup method (`close`/`aclose`)
      is registered with the scope.
    - If no `PureScope` is provided, the generator is closed immediately after yielding
      its first value to prevent resource leaks.

    Args:
        result: The result of a dependency call (may be a generator, async generator, or static value).
        scope: The `PureScope` instance for cleanup registration.

    Returns:
        The yielded value from the generator, or the original result if it was not a generator.
    """
    if isinstance(result, GeneratorType):
        try:
            value = next(result)

            if scope is not None:
                scope.add_cleanup(result.close, is_async=False)
            else:
                # No scope provided, close immediately to avoid leak
                result.close()
        except StopIteration:
            return None
        finally:
            with contextlib.suppress(Exception):
                # Ensure closure path if an error occurs mid-generation
                result.close()
        return value

    if inspect.isasyncgen(result):
        try:
            value = await result.__anext__()

            if scope is not None:
                scope.add_cleanup(result.aclose, is_async=True)
            else:
                # No scope provided, close immediately to avoid leak
                await result.aclose()
        except StopAsyncIteration:
            return None
        finally:
            with contextlib.suppress(Exception):
                # Ensure closure path if an error occurs mid-generation
                await result.aclose()
        return value

    return result


def inject(
    _func: Callable[..., Any] | None = None,
    *,
    overrides: dict[Any, Any] | None = None,
    dependencies_map: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """
    Decorator that automatically resolves parameters whose defaults are `Depends(...)`
    (request-agnostic) before calling the function.

    This allows functions defined using request-agnostic dependencies to be called
    without manually resolving the dependency tree.

    Args:
        _func: The function to decorate (used when decorating without arguments).
        overrides: A map to replace a dependency callable with a replacement.
        dependencies_map: A map of parameter names to specific values or dependencies.

    Returns:
        A decorated function that handles automatic dependency resolution.

    Usage:
        @inject
        async def f(repo = Depends(get_repo)): ...
        await f()
    """

    def _decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(func)
        ov: dict[Any, Any] = overrides or {}
        dm: dict[str, Any] = dependencies_map or {}

        if inspect.iscoroutinefunction(func) or is_async_callable(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Asynchronous wrapper that resolves dependencies via async I/O."""
                bound = signature.bind_partial(*args, **kwargs)

                for name, param in signature.parameters.items():
                    if name in bound.arguments:
                        continue

                    default = param.default
                    if isinstance(default, _Depends):
                        # Resolve nested request-agnostic dependency
                        value = await default.resolve(dependencies_map=dm, overrides=ov)
                        bound.arguments[name] = value
                    elif default is not inspect._empty:
                        bound.arguments[name] = default
                    else:
                        raise RuntimeError(
                            f"Missing required parameter '{name}' and no Depends/default provided "
                            f"for auto-injection in {getattr(func, '__name__', func)}"
                        )

                return await func(*bound.args, **bound.kwargs)

            # Preserve original signature for introspection tools
            async_wrapper.__signature__ = signature
            return async_wrapper

        # Sync branch
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Synchronous wrapper that resolves dependencies by running async I/O synchronously."""
            bound = signature.bind_partial(*args, **kwargs)

            for name, param in signature.parameters.items():
                if name in bound.arguments:
                    continue

                default = param.default
                if isinstance(default, _Depends):
                    # Resolve nested dependency by running async resolution synchronously
                    value = run_sync(default.resolve(dependencies_map=dm, overrides=ov))
                    bound.arguments[name] = value
                elif default is not inspect._empty:
                    bound.arguments[name] = default
                else:
                    raise RuntimeError(
                        f"Missing required parameter '{name}' and no Depends/default provided "
                        f"for auto-injection in {getattr(func, '__name__', func)}"
                    )

            return func(*bound.args, **bound.kwargs)

        sync_wrapper.__signature__ = signature
        return sync_wrapper

    # Handle decorator usage (with or without arguments)
    return _decorate if _func is None else _decorate(_func)
