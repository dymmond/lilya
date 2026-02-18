from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, ClassVar

from lilya import status as status
from lilya._internal._events import (
    AsyncLifespan as AsyncLifespan,
    handle_lifespan_events as handle_lifespan_events,
)
from lilya._internal._middleware import wrap_middleware
from lilya._internal._module_loading import import_string
from lilya._internal._path import (
    clean_path,
    compile_path,
    get_route_path,
    replace_params,
)
from lilya._internal._permissions import wrap_permission
from lilya._internal._urls import include
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.conf import _monkay as _monkay
from lilya.conf.global_settings import Settings as Settings
from lilya.contrib.documentation import Doc as Doc
from lilya.datastructures import (
    URL as URL,
    SendReceiveSniffer as SendReceiveSniffer,
    URLPath,
)
from lilya.dependencies import wrap_dependency
from lilya.enums import EventType as EventType, Match, ScopeType
from lilya.exceptions import (
    ContinueRouting as ContinueRouting,
    HTTPException as HTTPException,
    ImproperlyConfigured,
)
from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.requests import Request as Request
from lilya.responses import (
    PlainText as PlainText,
    RedirectResponse as RedirectResponse,
    Response as Response,
)
from lilya.types import (
    ASGIApp,
    Dependencies,
    ExceptionHandler,
    Lifespan as Lifespan,
    Receive,
    Scope,
    Send,
)
from lilya.websockets import WebSocket as WebSocket, WebSocketClose as WebSocketClose

from .base import BasePath as BasePath
from .host import Host as Host
from .mixins import RoutingMethodsMixin as RoutingMethodsMixin
from .path import Path as Path
from .router import BaseRouter as BaseRouter, Router as Router
from .types import (
    NoMatchFound as NoMatchFound,
    PassPartialMatches as PassPartialMatches,
    PathHandler as PathHandler,
    T as T,
    get_name as get_name,
)
from .websocket import WebSocketPath as WebSocketPath


class Include(BasePath):
    router_class: ClassVar[type[BaseRouter]] = Router

    __slots__ = (
        "path",
        "app",
        "namespace",
        "pattern",
        "name",
        "exception_handlers",
        "middleware",
        "permissions",
        "exception_handlers",
        "deprecated",
        "before_request",
        "after_request",
        "dependencies",
    )

    def __init__(
        self,
        path: str,
        app: ASGIApp | str | None = None,
        routes: Sequence[BasePath] | None = None,
        namespace: str | None = None,
        pattern: str | None = None,
        name: str | None = None,
        *,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
        include_in_schema: bool = True,
        deprecated: bool = False,
        redirect_slashes: bool = True,
    ) -> None:
        """
        Initialize the router with specified parameters.

        Args:
            path (str): The path associated with the router.
            app (Union[ASGIApp, str, None]): The ASGI app.
            routes (Union[Sequence[BasePath], None]): The routes.
            namespace (Union[str, None]): The namespace.
            pattern (Union[str, None]): The pattern.
            name (Union[str, None]): The name.
            middleware (Union[Sequence[DefineMiddleware], None]): The middleware.
            permissions (Union[Sequence[DefinePermission], None]): The permissions.
            exception_handlers (Union[Mapping[Any, ExceptionHandler], None]): The exception handlers.
            dependencies (Dependencies | None): Dependencies to inject.
            include_in_schema (bool): Flag to include in the schema.
            redirect_slashes (bool): (Only namespace or routes) Redirect slashes on mismatch.

        Returns:
            None
        """
        assert path == "" or path.startswith("/"), "Routed paths must start with '/'"
        assert app is not None or routes is not None or namespace is not None, (
            "Either 'app=...', or 'routes=...', or 'namespace=...' must be specified"
        )
        self.path = clean_path(path)

        assert namespace is None or routes is None, (
            "Either 'namespace=...' or 'routes=', not both."
        )

        if namespace and not isinstance(namespace, str):
            raise ImproperlyConfigured("Namespace must be a string. Example: 'myapp.routes'.")

        if pattern and not isinstance(pattern, str):
            raise ImproperlyConfigured("Pattern must be a string. Example: 'route_patterns'.")

        if pattern and routes:
            raise ImproperlyConfigured("Pattern must be used only with namespace.")

        if namespace is not None:
            routes = include(namespace, pattern)

        self.__base_app__: ASGIApp | Router
        if isinstance(app, str):
            self.__base_app__ = import_string(app)
            self.handle_not_found = self.handle_not_found_fallthrough  # type: ignore
        elif app is not None:
            self.handle_not_found = self.handle_not_found_fallthrough  # type: ignore
            self.__base_app__ = app
        else:
            self.__base_app__ = self.router_class(
                routes=routes,
                default=self.handle_not_found_fallthrough,
                is_sub_router=True,
                redirect_slashes=redirect_slashes,
            )

        self.app = self.__base_app__

        if middleware is not None:
            self.middleware = [wrap_middleware(mid) for mid in middleware]
        else:
            self.middleware = middleware or []

        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        if dependencies is None and hasattr(self.__base_app__, "dependencies"):
            _dependencies = self.__base_app__.dependencies or {}
        else:
            _dependencies = dependencies or {}

        # Wrap dependencies
        self.dependencies = {key: wrap_dependency(dep) for key, dep in _dependencies.items()}

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

        self.name = name
        self.include_in_schema = include_in_schema
        self.deprecated = deprecated

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            clean_path(self.path + "/{path:path}")
        )

    def _apply_middleware(self, middleware: Sequence[DefineMiddleware] | None) -> None:
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

    def _apply_permissions(self, permissions: Sequence[DefinePermission] | None) -> None:
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
    def routes(self) -> list[BasePath]:
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
    ) -> tuple[Match, Scope]:
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
        remaining_path = f"/{matched_params.pop('path', '')}"
        matched_path = route_path[: -len(remaining_path)]

        path_params = {**scope.get("path_params", {}), **matched_params}
        existing = list(scope.get("dependencies", []))
        child_scope = {
            "path_params": path_params,
            "app_root_path": scope.get("app_root_path", root_path),
            "root_path": root_path + matched_path,
            "handler": self.app,
            "dependencies": existing + [self.dependencies],
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
        try:
            for before_request in self.before_request:
                if inspect.isclass(before_request):
                    before_request = before_request()

                if is_async_callable(before_request):
                    await before_request(scope, receive, send)
                else:
                    await run_in_threadpool(before_request, scope, receive, send)

            await self.app(scope, receive, send)

            for after_request in self.after_request:
                if inspect.isclass(after_request):
                    after_request = after_request()

                if is_async_callable(after_request):
                    await after_request(scope, receive, send)
                else:
                    await run_in_threadpool(after_request, scope, receive, send)
        except Exception as ex:
            await self.handle_exception_handlers(scope, receive, send, ex)

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

        return self.url_path_for(name, **path_params)

    def url_path_for(self, name: str, /, **path_params: Any) -> URLPath:
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
                url = route.url_path_for(remaining_name, **remaining_params)
                return URLPath(path=path_prefix.rstrip("/") + str(url), protocol=url.protocol)
            except NoMatchFound:
                pass

        raise NoMatchFound(name, path_params)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(path={self.path!r}, name={name!r}, app={self.app!r})"
