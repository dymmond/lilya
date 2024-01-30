from __future__ import annotations

import functools
import inspect
import re
from typing import Any, Callable, Dict, List, Sequence, Set, Tuple, TypeVar, Union

from lilya import status
from lilya._internal._path import clean_path, compile_path, get_route_path, replace_params
from lilya._internal._responses import BaseHandler
from lilya.core.urls import include
from lilya.datastructures import Header, URLPath
from lilya.enums import HTTPMethod, Match, ScopeType
from lilya.exceptions import HTTPException, ImproperlyConfigured
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
        Dispatches the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        match, child_scope = self.search(scope)

        if match == Match.NONE:
            await self.handle_not_found(scope, receive, send)
            return

        scope.update(child_scope)
        await self.handle_dispatch(scope, receive, send)  # type: ignore

    async def handle_not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the case when no match is found.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        if scope["type"] == ScopeType.HTTP:
            response = PlainText("Not Found", status_code=status.HTTP_404_NOT_FOUND)
            await response(scope, receive, send)
        elif scope["type"] == ScopeType.WEBSOCKET:
            websocket_close = WebSocketClose()
            await websocket_close(scope, receive, send)

    def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.dispatch(scope=scope, receive=receive, send=send)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(path={self.path!r}, name={name!r}, app={self.app!r})"


class Path(BaseHandler, BasePath):
    """
    The way you can define a route in Lilya and apply the corresponding
    path definition.

    ## Example

    ```python
    from lilya.routing import Path

    Path('/home', callable=..., name="home")
    ```
    """

    __slots__ = (
        "path",
        "handler",
        "methods",
        "name",
        "include_in_schema",
        "middleware",
        "permissions",
    )

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: Union[List[str], Set[str], None] = None,
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
        self.signature: inspect.Signature = inspect.signature(self.handler)

        # Defition of the app
        handler_app = handler
        while isinstance(handler_app, functools.partial):
            handler_app = handler_app.func

        if inspect.isfunction(handler_app) or inspect.ismethod(handler_app):
            self.app = self.handle_response(handler_app)
        else:
            self.app = handler_app
            if methods is None:
                methods = {HTTPMethod.GET}

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        if self.methods is not None:
            self.methods = {method.upper() for method in methods}
            if HTTPMethod.GET in self.methods:
                self.methods.add(HTTPMethod.HEAD)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    def _apply_middleware(self, middleware: Union[Sequence[Middleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[Middleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

    def _apply_permissions(self, permissions: Union[Sequence[Permission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[Permission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)

    async def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.
        """
        self.validate_params(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params

        return URLPath(path=path, protocol=ScopeType.HTTP.value)

    def validate_params(self, name: str, path_params: dict) -> None:
        """
        Validates the route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Raises:
            NoMatchFound: If there is a mismatch in route name or parameters.
        """
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches against the regex.

        If found, then dispatches the request to the handler of the object.

        Args:
            scope (Scope): The request scope.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        if scope["type"] == ScopeType.HTTP:
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)

            if match:
                return self.handle_match(scope, match)
        return Match.NONE, {}

    def handle_match(self, scope: Scope, match: re.Match) -> Tuple[Match, Scope]:
        """
        Handles the case when a match is found in the route patterns.

        Args:
            scope (Scope): The request scope.
            match: The match object from the regex.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        matched_params = {
            key: self.param_convertors[key].transform(value)
            for key, value in match.groupdict().items()
        }
        path_params = {**scope.get("path_params", {}), **matched_params}
        child_scope = {"handler": self.handler, "path_params": path_params}

        if self.methods and scope["method"] not in self.methods:
            return Match.PARTIAL, child_scope
        else:
            return Match.FULL, child_scope

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainText("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class WebsocketPath(BaseHandler, BasePath):
    __slots__ = (
        "path",
        "handler",
        "name",
        "include_in_schema",
        "middleware",
        "permissions",
    )

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
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
        self.signature: inspect.Signature = inspect.signature(self.handler)

        # Defition of the app
        handler_app = handler
        while isinstance(handler_app, functools.partial):
            handler_app = handler_app.func

        if inspect.isfunction(handler_app) or inspect.ismethod(handler_app):
            self.app = self.handle_websocket_session(handler_app)
        else:
            self.app = handler_app

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    def _apply_middleware(self, middleware: Union[Sequence[Middleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[Middleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

    def _apply_permissions(self, permissions: Union[Sequence[Permission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[Permission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches against the regex.

        If found, then dispatches the request to the handler of the object.

        Args:
            scope (Scope): The request scope.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        if scope["type"] == ScopeType.WEBSOCKET:
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)

            if match:
                return self.handle_match(scope, match)

        return Match.NONE, {}

    def handle_match(self, scope: Scope, match: re.Match) -> Tuple[Match, Scope]:
        """
        Handles the case when a match is found in the route patterns.

        Args:
            scope (Scope): The request scope.
            match: The match object from the regex.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        matched_params = {
            key: self.param_convertors[key].transform(value)
            for key, value in match.groupdict().items()
        }
        path_params = {**scope.get("path_params", {}), **matched_params}
        child_scope = {"handler": self.handler, "path_params": path_params}
        return Match.FULL, child_scope

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        await self.app(scope, receive, send)

    async def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.

        """
        self.validate_params(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol=ScopeType.WEBSOCKET.value)

    def validate_params(self, name: str, path_params: dict) -> None:
        """
        Validates the route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Raises:
            NoMatchFound: If there is a mismatch in route name or parameters.
        """
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)


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
        """
        Initialize the router with specified parameters.

        Args:
            path (str): The path associated with the router.
            app (Union[ASGIApp, None]): The ASGI app.
            routes (Union[Sequence[BasePath], None]): The routes.
            namespace (Union[str, None]): The namespace.
            pattern (Union[str, None]): The pattern.
            name (Union[str, None]): The name.
            middleware (Union[Sequence[Middleware], None]): The middleware.
            permissions (Union[Sequence[Permission], None]): The permissions.
            include_in_schema (bool): Flag to include in the schema.

        Returns:
            None
        """
        assert path == "" or path.startswith("/"), "Routed paths must start with '/'"
        assert (
            app is not None or routes is not None
        ), "Either 'app=...', or 'routes=' must be specified"
        self.path = clean_path(path)

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

        self.__base_app__: Union[ASGIApp, Router] = (
            app if app is not None else Router(routes=routes)
        )
        self.app = self.__base_app__

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        self.name = name
        self.include_in_schema = include_in_schema
        self.middleware = middleware if middleware is not None else list(middleware)
        self.permissions = permissions if permissions is not None else list(permissions)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    def _apply_middleware(self, middleware: Union[Sequence[Middleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[Middleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, options in reversed(middleware):
                self.app = cls(app=self.app, **options)

    def _apply_permissions(self, permissions: Union[Sequence[Permission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[Permission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, options in reversed(permissions):
                self.app = cls(app=self.app, **options)

    @property
    def routes(self) -> List[BasePath]:
        """
        Returns a list of declared path objects.
        """
        return getattr(self.__base_app__, "routes", [])

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches against the regex.

        If found, then dispatches the request to the handler of the object.

        Args:
            scope (Scope): The request scope.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        if scope["type"] in {ScopeType.HTTP, ScopeType.WEBSOCKET}:
            root_path = scope.get("root_path", "")
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)

            if match:
                return self.handle_match(scope, match, route_path, root_path)

        return Match.NONE, {}

    def handle_match(
        self, scope: Scope, match: re.Match, route_path: str, root_path: str
    ) -> Tuple[Match, Scope]:
        """
        Handles the case when a match is found in the route patterns.

        Args:
            scope (Scope): The request scope.
            match: The match object from the regex.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        matched_params = {
            key: self.param_convertors[key].transform(value)
            for key, value in match.groupdict().items()
        }
        remaining_path = "/" + matched_params.pop("path")
        matched_path = route_path[: -len(remaining_path)]

        path_params = {**scope.get("path_params", {}), **matched_params}
        child_scope = {
            "path_params": path_params,
            "app_root_path": scope.get("app_root_path", root_path),
            "root_path": root_path + matched_path,
            "handler": self.app,
        }
        return Match.FULL, child_scope

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        await self.app(scope, receive, send)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.
        """
        remaining_params, remaining_name, path_prefix = self.validate_params(name, path_params)
        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, remaining_params
        )
        if not remaining_params:
            return URLPath(path=path)

        for route in self.routes or []:
            try:
                url = route.path_for(remaining_name, **remaining_params)
                return URLPath(path=path_prefix + str(url), protocol=url.protocol)
            except NoMatchFound:
                pass

        raise NoMatchFound(name, path_params)

    def validate_params(
        self, name: str, path_params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str, str]:
        """
        Validates the route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            Dict[str, Any]: The validated path parameters.

        Raises:
            NoMatchFound: If there is a mismatch in route name or parameters.
        """
        remaining_params: Dict[str, str] = {}

        if (self.name is not None and name == self.name and "path" in path_params) or (
            self.name is None or name.startswith(self.name + ":")
        ):
            if self.name is None:
                remaining_name = name
            else:
                remaining_name = name[len(self.name) + 1 :]

            path_kwarg = path_params.get("path")
            path_params["path"] = ""
            path_prefix, remaining_params = replace_params(
                self.path_format, self.param_convertors, path_params
            )

            if path_kwarg is not None:
                remaining_params["path"] = path_kwarg

        return remaining_params, remaining_name, path_prefix


class Host(BasePath):
    __slots__ = (
        "host",
        "app",
        "name",
    )

    def __init__(self, host: str, app: ASGIApp, name: Union[str, None] = None) -> None:
        assert not host.startswith("/"), "Host must not start with '/'"
        self.host = host
        self.app = app
        self.name = name
        self.host_regex, self.host_format, self.param_convertors, self.path_start = compile_path(
            host
        )

    @property
    def routes(self) -> List[BasePath]:
        """
        Returns a list of declared path objects.
        """
        return getattr(self.app, "routes", [])

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches within the route patterns and matches against the regex.

        If found, then dispatches the request to the handler of the object.

        Args:
            scope (Scope): The request scope.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        if scope["type"] in {ScopeType.HTTP, ScopeType.WEBSOCKET}:
            headers = Header.from_scope(scope=scope)
            host = headers.get("host", "").split(":")[0]
            match = self.host_regex.match(host)

            if match:
                return self.handle_match(scope, match)

        return Match.NONE, {}

    def handle_match(self, scope: Scope, match: re.Match) -> Tuple[Match, Scope]:
        """
        Handles the case when a match is found in the route patterns.

        Args:
            scope (Scope): The request scope.
            match: The match object from the regex.

        Returns:
            Tuple[Match, Scope]: The match result and child scope.
        """
        matched_params = {
            key: self.param_convertors[key].transform(value)
            for key, value in match.groupdict().items()
        }
        path_params = {**scope.get("path_params", {}), **matched_params}
        child_scope = {
            "path_params": path_params,
            "handler": self.app,
        }
        return Match.FULL, child_scope

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        await self.app(scope, receive, send)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Generates a URL path for the specified route name and parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            URLPath: The generated URL path.

        Raises:
            NoMatchFound: If there is no match for the given name and parameters.
        """
        remaining_params, remaining_name = self.validate_params(name, path_params)
        host, remaining_params = replace_params(
            self.host_format, self.param_convertors, remaining_params
        )

        if not remaining_params:
            return URLPath(path=path_params.pop("path"), host=host)

        for route in self.routes or []:
            try:
                url = route.path_for(remaining_name, **remaining_params)
                return URLPath(path=str(url), protocol=url.protocol, host=host)
            except NoMatchFound:
                pass

        raise NoMatchFound(name, path_params)

    def validate_params(
        self, name: str, path_params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Validates the route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params (dict): The path parameters.

        Returns:
            Dict[str, Any]: The validated path parameters.

        Raises:
            NoMatchFound: If there is a mismatch in route name or parameters.
        """
        remaining_params = {}

        if (self.name is not None and name == self.name and "path" in path_params) or (
            self.name is None or name.startswith(self.name + ":")
        ):
            if self.name is None:
                remaining_name = name
            else:
                remaining_name = name[len(self.name) + 1 :]

            path_params.pop("path")  # Remove 'path' from path_params
            remaining_params = self._replace_params(
                self.host_format, self.param_convertors, path_params
            )

        return remaining_params, remaining_name


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

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)

    def search(self, scope: Scope) -> Tuple[Match, Scope]:
        """
        Searches for a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Dispatches the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        match, child_scope = self.search(scope)

        if match == Match.NONE:
            await self.handle_not_found(scope, receive, send)
            return

        scope.update(child_scope)
        await self.handle_dispatch(scope, receive, send)  # type: ignore

    async def handle_not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the case when no match is found.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        if scope["type"] == ScopeType.HTTP:
            response = PlainText("Not Found", status_code=status.HTTP_404_NOT_FOUND)
            await response(scope, receive, send)
        elif scope["type"] == ScopeType.WEBSOCKET:
            websocket_close = WebSocketClose()
            await websocket_close(scope, receive, send)

    def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.dispatch(scope=scope, receive=receive, send=send)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(path={self.path!r}, name={name!r}, app={self.app!r})"
