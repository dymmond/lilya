import inspect
import sys
from collections.abc import Callable, Sequence
from functools import cached_property
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


class Provide:
    """
    Wraps a dependency factory callable. When resolved, it inspects
    the factory’s own signature and recursively resolves any nested
    Provide instances you’ve registered.
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
                except Exception:
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
