from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Sequence, Set, Tuple, Union

from lilya.datastructures import URLPath
from lilya.enums import HTTPMethod, Match
from lilya.middleware.base import Middleware
from lilya.permissions.base import Permission
from lilya.types import ASGIApp, Lifespan, Receive, Scope, Send


class NoMatchFound(Exception):
    """
    Raised by `.url_for(name, **path_params)` and `.url_path_for(name, **path_params)`
    if no matching route exists.
    """

    def __init__(self, name: str, path_params: Dict[str, Any]) -> None:
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


def get_name(handler: Callable[..., Any]) -> str:
    """
    Returns the name of a given handler.
    """
    return (
        handler.__name__
        if inspect.isroutine(handler) or inspect.isclass(handler)
        else handler.__class__.__name__
    )


class BasePath:
    """
    The base of all paths (routes) for any ASGI application
    with Lilya.
    """

    def search(self, scope: Scope) -> Tuple[Match, Scope]:
        """
        Searches for a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Returns a URL of a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the matched ASGI route.
        """
        raise NotImplementedError()  # pragma: no cover


class Router:
    """
    A Lilya router object.
    """

    def __init__(
        self,
        routes: Union[Sequence[BasePath], None] = None,
        redirect_slashes: bool = True,
        default: Union[ASGIApp, None] = None,
        on_startup: Union[Sequence[Callable[[], Any]], None] = None,
        on_shutdown: Union[Sequence[Callable[[], Any]], None] = None,
        lifespan: Union[Lifespan[Any], None] = None,
        *,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.raise_404 if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.include_in_schema = include_in_schema

        self.middleware = middleware if middleware is not None else list(middleware)
        self.permissions = permissions if permissions is not None else list(permissions)

        # # Execute the middlewares
        # if middleware is not None:
        #     for cls, options in reversed(middleware):
        #         self.middleware_stack = cls(app=self.app, **options)

        # # Execute the permissions
        # if permissions is not None:
        #     for cls, options in reversed(permissions):
        #         self.permission_stack = cls(app=self.app, **options)

    async def raise_404(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)


class Path(BasePath):
    """
    The way you can define a route in Lilya and apply the corresponding
    path definition.

    ## Example

    ```python
    from lilya.routing import Path

    Path('/home', callable=..., name="home")
    ```
    """

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        include_in_schema: bool = True,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = path
        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.methods: Union[List[str], Set[str], None] = methods

        # Defition of the app
        self.app = handler

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)

        if self.methods is not None:
            self.methods = {method.upper() for method in methods}
            if HTTPMethod.GET in self.methods:
                self.methods.add(HTTPMethod.HEAD)


class WebsocketPath(BasePath):
    ...


class Include(BasePath):
    ...


class Host(BasePath):
    ...
