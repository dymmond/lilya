import inspect
from collections.abc import Callable
from typing import Any

from typing_extensions import Self

from lilya.requests import Request


class Provide:
    """
    Wraps a dependency factory callable. When resolved, it inspects
    the factory’s own signature and recursively resolves any nested
    Provide instances you’ve registered.
    """

    def __init__(self, dependency: Callable[..., Any], use_cache: bool = False):
        self.dependency = dependency
        self.use_cache = use_cache
        self._cache: Any = None
        self._resolved: bool = False

    async def resolve(
        self,
        request: Request,
        dependencies_map: dict[str, Self],
    ) -> Any:
        # Return cached value if already resolved
        if self.use_cache and self._resolved:
            return self._cache

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
                else:
                    raise RuntimeError(
                        f"Could not resolve parameter '{name}' "
                        f"for dependency '{self.dependency.__name__}'"
                    )

        # Call (and await, if needed) the factory
        result = (
            await self.dependency(**kwargs)
            if inspect.iscoroutinefunction(self.dependency)
            else self.dependency(**kwargs)
        )

        if self.use_cache:
            self._cache = result
            self._resolved = True

        return result


class Provides:
    """
    Parameter‐default marker. Use this in your handler signature to
    signal “please take my `dependencies['foo']` and inject it here.”
    """

    def __init__(self) -> None: ...
