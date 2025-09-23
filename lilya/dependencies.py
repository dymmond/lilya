import contextlib
import inspect
import sys
from collections.abc import Callable, Coroutine, Sequence
from functools import cached_property, lru_cache, wraps
from types import GeneratorType
from typing import Any, cast

from lilya.compat import is_async_callable, run_sync
from lilya.enums import SignatureDefault
from lilya.requests import Request
from lilya.websockets import WebSocket

SIGNATURE_TO_LIST = SignatureDefault.to_list()

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@lru_cache(maxsize=1024)
def wrap_dependency(
    dependency: Callable[..., Any],
    *args: Any,
    use_cache: bool = False,
    **kwargs: Any,
) -> "Provide":
    """
    Wraps a dependency factory callable. When resolved, it inspects
    the factory's own signature and recursively resolves any nested
    Provide instances you've registered.
    """
    if not isinstance(dependency, Provide):
        if not callable(dependency):
            return Provide(lambda: dependency, *args, use_cache=use_cache, **kwargs)  # type: ignore
        return Provide(dependency, *args, use_cache=use_cache, **kwargs)
    return dependency  # type: ignore


class Provide:
    """
    Wraps a dependency factory callable. When resolved, it inspects
    the factory's own signature and recursively resolves any nested
    Provide instances you've registered.
    """

    def __init__(
        self,
        dependency: Callable[..., Any],
        *args: Any,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> None:
        self.dependency = dependency
        self.provided_args = args
        self.provided_kwargs = kwargs
        self.use_cache = use_cache
        self._cache: Any = None
        self._resolved: bool = False
        self.__dependency_signature__: inspect.Signature | None = None

    @cached_property
    def __signature__(self) -> inspect.Signature:
        """
        Returns the signature of the dependency function.
        This is used to introspect the parameters of the dependency.
        """
        if self.__dependency_signature__ is None:
            self.__dependency_signature__ = inspect.signature(self.dependency)
        return self.__dependency_signature__

    async def resolve(
        self,
        request: Request,
        dependencies_map: dict[str, Self | Any],
    ) -> Any:
        # Return cached value if already resolved
        if self.use_cache and self._resolved:
            return self._cache

        # If the dependency is a class, we need to instantiate it
        # and pass the request to it
        if self.__signature__.parameters:
            json_data: dict[str, Any] = {}
            signature_keys = self.__signature__.parameters.keys()

            if isinstance(request, Request):
                try:
                    json_data = cast(dict[str, Any], await request.data()) or {}
                except Exception:  # noqa
                    ...

                updated_keys: dict[str, Any] = {}

                for key, value in json_data.items():
                    # Only include keys that are in the signature
                    # and not already provided via provided_kwargs or provided_args
                    # This prevents overwriting explicitly provided values
                    # We also ensure that we don't include keys that are not in the signature
                    # This is important to avoid passing unexpected arguments
                    # We also ensure that we don't include keys that are not in the signature
                    if key in signature_keys and key not in dependencies_map:
                        updated_keys[key] = value

                if updated_keys:
                    self.provided_kwargs.update(updated_keys)

        # If the user passed explicit args/kwargs *or* pointed us at a class,
        # just call the factory directly and skip the auto-resolution logic.
        if self.provided_args or self.provided_kwargs or inspect.isclass(self.dependency):
            if inspect.iscoroutinefunction(self.dependency) or is_async_callable(self.dependency):
                result = await self.dependency(*self.provided_args, **self.provided_kwargs)
            else:
                result = self.dependency(*self.provided_args, **self.provided_kwargs)

            if self.use_cache:
                self._cache = result
                self._resolved = True
            return result

        sig = inspect.signature(self.dependency)
        kwargs: dict[str, Any] = {}

        # Resolve each parameter of this dependency
        for name, param in sig.parameters.items():
            # Resolve each *named* parameter of this dependency (skip *args/**kwargs)
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            # Making sure we cover the Resolve and Security cases
            if isinstance(param.default, (Resolve, Security)):
                kwargs[name] = await async_resolve_dependencies(
                    request=request,
                    func=self.dependency,
                )
                continue

            if name in dependencies_map:
                # nested dependency
                dep = dependencies_map[name]
                kwargs[name] = await dep.resolve(request, dependencies_map)
            else:
                # fallback: try to pull from request attributes/query/body
                if hasattr(request, name):
                    kwargs[name] = getattr(request, name)
                elif name in request.query_params:
                    kwargs[name] = request.query_params[name]
                elif name in SIGNATURE_TO_LIST:
                    kwargs[name] = request
                else:
                    raise RuntimeError(
                        f"Could not resolve parameter '{name}' for dependency '{self.dependency.__name__}'"
                    )

        call_kwargs = {**self.provided_kwargs, **kwargs}

        # If the dependency is a coroutine function, await it; otherwise, call it directly.
        # This allows for both synchronous and asynchronous dependencies.
        if inspect.iscoroutinefunction(self.dependency) or is_async_callable(self.dependency):
            result = await self.dependency(*self.provided_args, **call_kwargs)
        else:
            result = self.dependency(*self.provided_args, **call_kwargs)

        if self.use_cache:
            self._cache = result
            self._resolved = True

        # We need to account for generators
        if isinstance(result, GeneratorType):
            try:
                value = next(result)
            except StopIteration:
                return None
            request.add_cleanup(result.close)  # noqa
            return value

        if inspect.isasyncgen(result):
            try:
                value = await result.__anext__()
            except StopAsyncIteration:
                return None
            request.add_cleanup(result.aclose)  # noqa
            return value

        return result


class Provides:
    """
    Parameter‐default marker. Use this in your handler signature to
    signal “please take my `dependencies['foo']` and inject it here.”
    """

    def __init__(self) -> None: ...


class Resolve(Provide):
    """
    Parameter default marker. Use this in your handler signature to
    signal “please resolve this dependency and inject it here.”
    """

    def __repr__(self) -> str:
        return "Resolve()"


class Security(Provide):
    """
    Parameter default marker. Use this in your handler signature to
    signal “please resolve this security dependency and inject it here.”
    """

    def __init__(
        self,
        dependency: Callable[..., Any],
        *args: Any,
        scopes: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, dependency=dependency, **kwargs)
        self.scopes = scopes or []


async def async_resolve_dependencies(
    request: Request | WebSocket,
    func: Callable[..., Any],
    overrides: dict[str, Any] | None = None,
) -> Any:
    """
    Resolves dependencies for an asynchronous function by inspecting its signature and
    recursively resolving any dependencies specified using the `params.Requires` class.
    Args:
        func (Any): The target function whose dependencies need to be resolved.
        overrides (Union[dict[str, Any]], optional): A dictionary of overrides for dependencies.
            This can be used for testing or customization. Defaults to None.
    Returns:
        Any: The result of the target function with its dependencies resolved.
    Raises:
        TypeError: If the target function or any of its dependencies are not callable.
    """
    if overrides is None:
        overrides = {}

    kwargs = {}

    signature = inspect.signature(func)

    for name, param in signature.parameters.items():
        # If in one of the requirements happens to be Security, we need to resolve it
        # By passing the Request object to the dependency
        if isinstance(param.default, Security):
            kwargs[name] = await param.default.dependency(request)
        if isinstance(param.default, Resolve):
            dep_func = param.default.dependency
            dep_func = overrides.get(dep_func, dep_func)  # type: ignore
            if inspect.iscoroutinefunction(dep_func):
                resolved = await async_resolve_dependencies(
                    request=request,
                    func=dep_func,
                    overrides=overrides,
                )
            else:
                resolved = (
                    resolve_dependencies(request, dep_func, overrides)
                    if callable(dep_func)
                    else dep_func
                )
            kwargs[name] = resolved
    if inspect.iscoroutinefunction(func):
        result = await func(**kwargs)
    else:
        result = func(**kwargs)

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
    Resolves the dependencies for a given function.

    Parameters:
        func (Any): The function for which dependencies need to be resolved.
        overrides (Union[dict[str, Any], None], optional): A dictionary of dependency overrides. Defaults to None.
        Raises:
        ValueError: If the provided function is asynchronous.

    Returns:
        Any: The result of running the asynchronous dependency resolution function.
    """
    if overrides is None:
        overrides = {}
    if inspect.iscoroutinefunction(func):
        raise ValueError("Function is async. Use resolve_dependencies_async instead.")
    return run_sync(async_resolve_dependencies(request, func, overrides))


class PureScope:
    """
    Async context manager for managing cleanup of resources in a request-less scope.

    Usage:
        async with PureScope() as scope:
            # Use scope to manage resources
            ...
        # Resources are cleaned up here
    """

    def __init__(self) -> None:
        self._cleanups: list[
            tuple[Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]], bool]
        ] = []

    def add_cleanup(
        self, fn: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]], is_async: bool
    ) -> None:
        """
        Register a cleanup function to be called when the scope is closed.
        """
        self._cleanups.append((fn, is_async))

    async def aclose(self) -> None:
        """
        Call all registered cleanup functions in LIFO order.
        Suppresses any exceptions raised by cleanup functions.
        """
        while self._cleanups:
            fn, is_async = self._cleanups.pop()
            try:
                if is_async:
                    await fn()
                else:
                    fn()
            except Exception:  # noqa
                ...

    async def __aenter__(self) -> "PureScope":
        """
        Enter the async context manager.
        """
        return self

    async def __aexit__(self, et: Any, ev: Any, tb: Any) -> None:
        """
        Exit the async context manager and perform cleanup.
        """
        await self.aclose()


def _constant(value: Any) -> Callable[[], Any]:
    """
    Wrap a non-callable value in a zero-argument function using `def`
    (preferred over lambda for clarity and style guides).
    """

    def return_value(_v: Any = value) -> Any:
        """
        Return the constant value.
        """
        return _v

    return_value.__name__ = "constant"
    return return_value


class _Depends:
    """
    Parameter default marker and/or dependency wrapper that is completely
    request-agnostic. Can be used anywhere (services, tasks, tests).

    Usage in signatures:
        def handler(repo = Depends(get_repo)): ...

    Or as a wrapper:
        repo_dep = Depends(get_repo, use_cache=True)
        await repo_dep.resolve()  # no Request needed
    """

    def __init__(
        self,
        dependency: Callable[..., Any] | Any,
        *args: Any,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> None:
        if not isinstance(dependency, _Depends) and not callable(dependency):
            dependency = _constant(dependency)
        self.dependency = dependency  # Callable[..., Any]
        self.provided_args = args
        self.provided_kwargs = kwargs
        self.use_cache = use_cache
        self._cache: Any = None
        self._resolved: bool = False
        self.__dependency_signature__: inspect.Signature | None = None

    def __repr__(self) -> str:
        name = getattr(self.dependency, "__name__", type(self.dependency).__name__)
        return f"Depends({name})"

    @cached_property
    def __signature__(self) -> inspect.Signature:
        if self.__dependency_signature__ is None:
            self.__dependency_signature__ = inspect.signature(self.dependency)  # type: ignore[arg-type]
        return self.__dependency_signature__

    async def resolve(
        self,
        dependencies_map: dict[str, Any | Any] | None = None,
        overrides: dict[Any, Any] | None = None,
        scope: PureScope | None = None,
    ) -> Any:
        """
        Resolve the dependency tree without any Request/WebSocket.

        - `dependencies_map` lets you bind parameter names to other Depends/values.
        - `overrides` lets you replace a callable with another callable/value by identity.
        """
        if self.use_cache and self._resolved:
            return self._cache

        dependencies_map = dependencies_map or {}
        overrides = overrides or {}

        # If args/kwargs explicitly provided or this is a class, call directly.
        if self.provided_args or self.provided_kwargs or inspect.isclass(self.dependency):
            dep_callable = overrides.get(self.dependency, self.dependency)
            result = await _maybe_call_async(
                dep_callable, *self.provided_args, **self.provided_kwargs
            )
            result = await _handle_generators_requestless(result)
            if self.use_cache:
                self._cache, self._resolved = result, True
            return result

        # Otherwise, introspect the dependency function and build kwargs.
        signature = inspect.signature(self.dependency)  # type: ignore
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
                # If the default itself is callable but *not* a Depends, we respect it literally,
                # i.e., pass the callable object as default rather than invoking it.
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
    Safe factory for request-less Depends.

    - If `dependency` is non-callable (e.g., dict), we bypass caching (unhashable).
    - If `dependency` is callable, we attempt to cache by a computed key; if
      any piece of the key is unhashable, we skip caching.

    Usage in signatures:
        def handler(repo = Depends(get_repo)): ...
    Or as a wrapper:
        repo_dep = Depends(get_repo, use_cache=True)
        await repo_dep.resolve()  # no Request needed
    """
    if not callable(dependency):
        return _Depends(_constant(dependency), *args, use_cache=use_cache, **kwargs)

    try:
        key = (
            dependency,
            tuple(args),
            frozenset(kwargs.items()),
            bool(use_cache),
        )
        hash(key)
    except TypeError:
        return _Depends(dependency, *args, use_cache=use_cache, **kwargs)

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
    See Depends() for usage and behavior.

    Args:
        key: A tuple containing the dependency callable, its args, kwargs as a frozenset, and use_cache flag.
    """
    dependency, args, kw_items, use_cache = key
    return _Depends(dependency, *args, use_cache=use_cache, **dict(kw_items))


async def _maybe_call_async(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """
    Call a function that may be sync or async, and await if needed.

    Args:
        fn: The function to call.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
    """
    if inspect.iscoroutinefunction(fn) or is_async_callable(fn):
        return await fn(*args, **kwargs)
    return fn(*args, **kwargs)


async def _handle_generators_requestless(result: Any, scope: PureScope | None = None) -> Any:
    """
    For request-less operation, we can't rely on request.add_cleanup.

    Strategy: yield-first-then-close immediately to avoid leaks.

    If you need scoped lifetime, prefer context managers instead of generators.
    """
    if isinstance(result, GeneratorType):
        try:
            value = next(result)

            if scope is not None:
                scope.add_cleanup(result.close, is_async=False)
            else:
                result.close()
        except StopIteration:
            return None
        finally:
            with contextlib.suppress(Exception):
                result.close()
        return value

    if inspect.isasyncgen(result):
        try:
            value = await result.__anext__()

            if scope is not None:
                scope.add_cleanup(result.aclose, is_async=True)
            else:
                await result.aclose()
        except StopAsyncIteration:
            return None
        finally:
            with contextlib.suppress(Exception):
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
    Decorator that auto-resolves parameters whose defaults are `Depends(...)`
    (request-agnostic) before calling the function.

    Usage:
        @inject
        async def f(x = Depends(dep)): ...
        await f()  # x is injected

    You can also set static overrides or a name-based dependencies_map:
        @inject(overrides={dep: replacement}, dependencies_map={"x": 123})
        def g(x=Depends(dep)): ...
    """

    def _decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(func)
        ov = overrides or {}
        dm = dependencies_map or {}

        if inspect.iscoroutinefunction(func) or is_async_callable(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                bound = signature.bind_partial(*args, **kwargs)

                for name, param in signature.parameters.items():
                    if name in bound.arguments:
                        continue

                    default = param.default
                    if isinstance(default, _Depends):
                        # Let Depends handle recursion/nesting
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
            bound = signature.bind_partial(*args, **kwargs)

            for name, param in signature.parameters.items():
                if name in bound.arguments:
                    continue

                default = param.default
                if isinstance(default, _Depends):
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

    return _decorate if _func is None else _decorate(_func)
