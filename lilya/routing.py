from __future__ import annotations

import functools
import inspect
import re
import traceback
from typing import Any, Awaitable, Callable, Dict, List, Sequence, Tuple, TypeVar, Union

from lilya import status
from lilya._internal._events import AsyncLifespan, handle_lifespan_events
from lilya._internal._path import clean_path, compile_path, get_route_path, replace_params
from lilya._internal._responses import BaseHandler
from lilya.compat import is_async_callable
from lilya.conf import settings
from lilya.core.urls import include
from lilya.datastructures import URL, Header, URLPath
from lilya.enums import EventType, HTTPMethod, Match, ScopeType
from lilya.exceptions import HTTPException, ImproperlyConfigured
from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.requests import Request
from lilya.responses import PlainText, RedirectResponse, Response
from lilya.types import ASGIApp, Lifespan, Receive, Scope, Send
from lilya.websockets import WebSocket, WebSocketClose

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

    def handle_signature(self) -> None:
        raise NotImplementedError()  # pragma: no cover

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
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        include_in_schema: bool = True,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = clean_path(path)
        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.methods: Union[List[str], None] = methods

        # Defition of the app
        handler_app = handler
        while isinstance(handler_app, functools.partial):
            handler_app = handler_app.func

        self.signature: inspect.Signature = inspect.signature(handler_app)

        # Handles the signature validation
        self.handle_signature()

        if inspect.isfunction(handler_app) or inspect.ismethod(handler_app):
            self.app = self.handle_response(handler)
            if methods is None:
                self.methods = [HTTPMethod.GET.value]
        else:
            self.app = handler

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        if self.methods is not None:
            self.methods = [method.upper() for method in self.methods]
            if HTTPMethod.GET in self.methods:
                self.methods.append(HTTPMethod.HEAD.value)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not settings.enforce_return_annotation:
            return None

        if self.signature is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )

    def _apply_middleware(self, middleware: Union[Sequence[DefineMiddleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, args, options in reversed(middleware):
                self.app = cls(app=self.app, *args, **options)

    def _apply_permissions(self, permissions: Union[Sequence[DefinePermission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(permissions):
                self.app = cls(app=self.app, *args, **options)

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

    def __repr__(self) -> str:
        methods = sorted(self.methods or [])
        return f"{self.__class__.__name__}(path={self.path!r}, name={self.name!r}, methods={methods!r})"


class WebSocketPath(BaseHandler, BasePath):
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
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = clean_path(path)

        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema

        # Defition of the app
        handler_app = handler
        while isinstance(handler_app, functools.partial):
            handler_app = handler_app.func

        self.signature: inspect.Signature = inspect.signature(handler_app)

        # Handles the signature
        self.handle_signature()

        if inspect.isfunction(handler_app) or inspect.ismethod(handler_app):
            self.app = self.handle_websocket_session(handler)
        else:
            self.app = handler

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not settings.enforce_return_annotation:
            return None

        if self.signature is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )

    def _apply_middleware(self, middleware: Union[Sequence[DefineMiddleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, args, options in reversed(middleware):
                self.app = cls(app=self.app, *args, **options)

    def _apply_permissions(self, permissions: Union[Sequence[DefinePermission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(permissions):
                self.app = cls(app=self.app, *args, **options)

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r}, name={self.name!r})"


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
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
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
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.
            permissions (Union[Sequence[DefinePermission], None]): The permissions.
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

        self.middleware = middleware if middleware is not None else []
        self.permissions = permissions if permissions is not None else []

        self._apply_middleware(middleware)
        self._apply_permissions(permissions)

        self.name = name
        self.include_in_schema = include_in_schema

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            clean_path(self.path + "/{path:path}")
        )

    def _apply_middleware(self, middleware: Union[Sequence[DefineMiddleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, args, options in reversed(middleware):
                self.app = cls(app=self.app, *args, **options)

    def _apply_permissions(self, permissions: Union[Sequence[DefinePermission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(permissions):
                self.app = cls(app=self.app, *args, **options)

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
        remaining_path = "/" + matched_params.pop("path", "")
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
        Generate a URLPath for a given route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params: Path parameters for route substitution.

        Returns:
            URLPath: The generated URLPath.

        Raises:
            NoMatchFound: If no matching route is found for the given name and parameters.
        """

        if self.name is not None and name == self.name and "path" in path_params:
            path_params["path"] = path_params["path"].lstrip("/")
            path, remaining_params = replace_params(
                self.path_format, self.param_convertors, path_params
            )
            if not remaining_params:
                return URLPath(path=path)
        elif self.name is None or name.startswith(self.name + ":"):
            return self._path_for_without_name(name, path_params)

        raise NoMatchFound(name, path_params)

    def _path_for_without_name(self, name: str, path_params: dict) -> URLPath:
        """
        Generate a URLPath for a route without a specific name and with path parameters.

        Args:
            name (str): The name of the route.
            path_params: Path parameters for route substitution.

        Returns:
            URLPath: The generated URLPath.

        Raises:
            NoMatchFound: If no matching route is found for the given name and parameters.
        """
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

        for route in self.routes or []:
            try:
                url = route.path_for(remaining_name, **remaining_params)
                return URLPath(path=path_prefix.rstrip("/") + str(url), protocol=url.protocol)
            except NoMatchFound:
                pass

        raise NoMatchFound(name, path_params)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(path={self.path!r}, name={name!r}, app={self.app!r})"


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
        Generate a URLPath for a given route name and path parameters.

        Args:
            name (str): The name of the route.
            path_params: Path parameters for route substitution.

        Returns:
            URLPath: The generated URLPath.

        Raises:
            NoMatchFound: If no matching route is found for the given name and parameters.
        """
        if self.name is not None and name == self.name and "path" in path_params:
            return self.path_for_with_name(path_params)
        elif self.name is None or name.startswith(self.name + ":"):
            return self.path_for_without_name(name, path_params)
        else:
            raise NoMatchFound(name, path_params)

    def path_for_with_name(self, path_params: dict) -> URLPath:
        """
        Generate a URLPath for a route with a specific name and path parameters.

        Args:
            path_params: Path parameters for route substitution.

        Returns:
            URLPath: The generated URLPath.

        Raises:
            NoMatchFound: If no matching route is found for the given parameters.
        """
        path = path_params.pop("path")
        host, remaining_params = replace_params(
            self.host_format, self.param_convertors, path_params, is_host=True
        )
        if not remaining_params:
            return URLPath(path=path, host=host)

        raise NoMatchFound(self.name, path_params)

    def path_for_without_name(self, name: str, path_params: dict) -> URLPath:
        """
        Generate a URLPath for a route without a specific name and with path parameters.

        Args:
            name (str): The name of the route.
            path_params: Path parameters for route substitution.

        Returns:
            URLPath: The generated URLPath.

        Raises:
            NoMatchFound: If no matching route is found for the given name and parameters.
        """
        if self.name is None:
            remaining_name = name
        else:
            remaining_name = name[len(self.name) + 1 :]

        host, remaining_params = replace_params(
            self.host_format, self.param_convertors, path_params, is_host=True
        )

        for route in self.routes or []:
            try:
                url = route.path_for(remaining_name, **remaining_params)
                return URLPath(path=str(url), protocol=url.protocol, host=host)
            except NoMatchFound:
                pass

        raise NoMatchFound(name, path_params)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(host={self.host!r}, name={name!r}, app={self.app!r})"


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
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        assert lifespan is None or (
            on_startup is None and on_shutdown is None
        ), "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."

        if inspect.isasyncgenfunction(lifespan) or inspect.isgeneratorfunction(lifespan):
            raise ImproperlyConfigured("async function generators are not allowed.")

        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

        self.lifespan_context = handle_lifespan_events(
            on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan
        )

        if self.lifespan_context is None:
            self.lifespan_context = AsyncLifespan(self)

        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.handle_not_found if default is None else default
        self.include_in_schema = include_in_schema

        self.middleware = middleware if middleware is not None else []
        self.permissions = permissions if permissions is not None else []

        self.middleware_stack = self.app

        self._apply_middleware(self.middleware)
        self._apply_permissions(self.permissions)

    def _apply_middleware(self, middleware: Union[Sequence[DefineMiddleware], None]) -> None:
        """
        Apply middleware to the app.

        Args:
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.

        Returns:
            None
        """
        if middleware is not None:
            for cls, args, options in reversed(middleware):
                self.middleware_stack = cls(app=self.middleware_stack, *args, **options)

    def _apply_permissions(self, permissions: Union[Sequence[DefinePermission], None]) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(permissions):
                self.middleware_stack = cls(app=self.middleware_stack, *args, **options)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)

    async def startup(self) -> None:
        """
        Runs the the events on startup.
        """
        for handler in self.on_startup:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def shutdown(self) -> None:
        """
        Runs the the events on startup.
        """
        for handler in self.on_shutdown:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def handle_route(
        self, route: BasePath, child_scope: Scope, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """
        Handle a route match.

        Args:
            route: The matched route.
            child_scope (Scope): The ASGI child scope.
            scope (Scope): The ASGI scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.
        """
        scope.update(child_scope)
        await route.handle_dispatch(scope, receive, send)  # type: ignore

    async def handle_partial(
        self, route: BasePath, partial_scope: Scope, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """
        Handle a partial route match.

        Args:
            route: The partial matched route.
            partial_scope: The partial route scope.
            scope (Scope): The ASGI scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.
        """
        scope.update(partial_scope)
        await route.handle_dispatch(scope, receive, send)  # type: ignore

    async def handle_default(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle the default behavior.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.
        """
        await self.default(scope, receive, send)

    async def lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle ASGI lifespan messages, managing application startup and shutdown events.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        completed_startup = False

        async def startup_complete() -> None:
            await send({"type": "lifespan.startup.complete"})

        async def shutdown_complete() -> None:
            await send({"type": "lifespan.shutdown.complete"})

        async def lifespan_error(type: str, message: str) -> None:
            await send({"type": type, "message": message})

        try:
            app: Any = scope.get("app")
            await receive()
            async with self.lifespan_context(app) as state:
                if state is not None:
                    if "state" not in scope:
                        raise RuntimeError(
                            'The server does not support "state" in the lifespan scope.'
                        )
                    scope["state"].update(state)

                await startup_complete()
                completed_startup = True
                await receive()

        except BaseException:
            exc_text = traceback.format_exc()
            if completed_startup:
                await lifespan_error("lifespan.shutdown.failed", exc_text)
            else:
                await lifespan_error("lifespan.startup.failed", exc_text)
            raise

        else:
            await shutdown_complete()

    async def app(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle ASGI messages, managing different scopes and routing.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.
        """
        assert scope["type"] in (ScopeType.HTTP, ScopeType.WEBSOCKET, ScopeType.LIFESPAN)

        if "router" not in scope:
            scope["router"] = self

        if scope["type"] == ScopeType.LIFESPAN:
            await self.lifespan(scope, receive, send)
            return

        partial = None

        for route in self.routes:
            match, child_scope = route.search(scope)
            if match == Match.FULL:
                await self.handle_route(route, child_scope, scope, receive, send)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        if partial is not None:
            await self.handle_partial(partial, partial_scope, scope, receive, send)
            return

        route_path = get_route_path(scope)
        if scope["type"] == ScopeType.HTTP and self.redirect_slashes and route_path != "/":
            redirect_scope = dict(scope)
            if route_path.endswith("/"):
                redirect_scope["path"] = redirect_scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = redirect_scope["path"] + "/"

            for route in self.routes:
                match, child_scope = route.search(redirect_scope)
                if match != Match.NONE:
                    redirect_url = URL.build_from_scope(scope=redirect_scope)
                    response = RedirectResponse(url=str(redirect_url))
                    await response(scope, receive, send)
                    return

        await self.handle_default(scope, receive, send)

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

    def include(
        self,
        path: str,
        app: ASGIApp,
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
        namespace: Union[str, None] = None,
        pattern: Union[str, None] = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Adds an Include application into the routes.
        """
        route = Include(
            path,
            app=app,
            name=name,
            middleware=middleware,
            permissions=permissions,
            namespace=namespace,
            pattern=pattern,
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)

    def host(self, host: str, app: ASGIApp, name: Union[str, None] = None) -> None:
        """
        Adds a Host application into the routes.
        """
        route = Host(host, app=app, name=name)
        self.routes.append(route)

    def add_route(
        self,
        path: str,
        handler: Callable[[Request], Union[Awaitable[Response], Response]],
        methods: Union[List[str], None] = None,
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Manually creates a `Path`` from a given handler.
        """
        route = Path(
            path,
            handler=handler,
            methods=methods,
            middleware=middleware,
            permissions=permissions,
            name=name,
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)

    def add_websocket_route(
        self,
        path: str,
        handler: Callable[[WebSocket], Awaitable[None]],
        name: Union[str, None] = None,
        middleware: Union[Sequence[DefineMiddleware], None] = None,
        permissions: Union[Sequence[DefinePermission], None] = None,
    ) -> None:
        """
        Manually creates a `WebSocketPath` from a given handler.
        """
        route = WebSocketPath(
            path, handler=handler, middleware=middleware, permissions=permissions, name=name
        )
        self.routes.append(route)

    def add_event_handler(
        self, event_type: str, func: Callable[[], Any]
    ) -> None:  # pragma: no cover
        assert event_type in (EventType.ON_STARTUP, EventType.ON_SHUTDOWN)

        if event_type == EventType.ON_STARTUP:
            self.on_startup.append(func)
        else:
            self.on_shutdown.append(func)

    def on_event(self, event_type: str) -> Callable:
        def wrapper(func: Callable) -> Callable:
            self.add_event_handler(event_type, func)
            return func

        return wrapper

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.middleware_stack(scope, receive, send)
