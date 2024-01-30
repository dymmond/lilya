from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Sequence, Set, Tuple, TypeVar, Union

from lilya._internal._path import clean_path, compile_path, get_route_path, replace_params
from lilya.core.urls import include
from lilya.datastructures import URLPath
from lilya.enums import HTTPMethod, Match, ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.middleware.base import Middleware
from lilya.permissions.base import Permission
from lilya.responses import PlainText
from lilya.types import ASGIApp, Lifespan, Receive, Scope, Send
from lilya.websockets import WebSocketClose

T = TypeVar("T")


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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        breakpoint()
        match, child_scope = self.search(scope)
        if match == Match.NONE:
            if scope["type"] == ScopeType.HTTP:
                response = PlainText("Not Found", status_code=404)
                await response(scope, receive, send)
            elif scope["type"] == ScopeType.WEBSOCKET:
                websocket_close = WebSocketClose()
                await websocket_close(scope, receive, send)
            return

        scope.update(child_scope)
        await self.dispatch(scope, receive, send)


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
        self.path = clean_path(path)
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

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    async def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol=ScopeType.HTTP)

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        breakpoint()
        return await super().dispatch(scope, receive, send)

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches
        against the regex.

        If found, then dispatches the request to the handler
        of the object.
        """
        path_params: Dict[str, Any]
        if scope["type"] == ScopeType.HTTP:
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].render(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"handler": self.handler, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}


class WebsocketPath(BasePath):
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

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)


class Include(BasePath):
    __slots__ = (
        "path",
        "app",
        "namespace",
        "pattern",
        "name",
        "exception_handlers",
        "permissions",
        "middleware",
    )

    def __init__(
        self,
        path: str,
        app: Union[ASGIApp, None] = None,
        routes: Union[Sequence[BasePath], None] = None,
        namespace: Union[str, None] = None,
        pattern: Union[str, None] = None,
        name: Union[str, None] = None,
        *,
        middleware: Union[Sequence[Middleware], None] = None,
        permissions: Union[Sequence[Permission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        assert path == "" or path.startswith("/"), "Routed paths must start with '/'"
        assert (
            app is not None or routes is not None
        ), "Either 'app=...', or 'routes=' must be specified"
        self.path = path.rstrip("/")

        assert (
            namespace is None or routes is None
        ), "Either 'namespace=...' or 'routes=', not both."

        if namespace and not isinstance(namespace, str):
            raise ImproperlyConfigured("Namespace must be a string. Example: 'myapp.routes'.")

        if pattern and not isinstance(pattern, str):
            raise ImproperlyConfigured("Pattern must be a string. Example: 'route_patterns'.")

        if pattern and routes:
            raise ImproperlyConfigured("Pattern must be used only with namespace.")

        if namespace is not None:
            routes = include(namespace, pattern)

        if app is not None:
            self._base_app: ASGIApp = app
        else:
            self._base_app = Router(routes=routes)  # type: ignore
        self.app = self._base_app

        # if middleware is not None:
        #     for cls, options in reversed(middleware):
        #         self.app = cls(app=self.app, **options)

        # if permissions is not None:
        #     for cls, options in reversed(permissions):
        #         self.app = cls(app=self.app, **options)

        self.name = name
        self.include_in_schema = include_in_schema
        self.middleware = middleware if middleware is not None else list(middleware)
        self.permissions = permissions if permissions is not None else list(permissions)


class Host(BasePath): ...


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

        # Execute the middlewares
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.middleware_stack = cls(app=self.app, **options)

        # Execute the permissions
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.permission_stack = cls(app=self.app, **options)

    async def raise_404(self, scope: Scope, receive: Receive, send: Send) -> None: ...

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)
