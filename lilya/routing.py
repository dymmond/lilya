from __future__ import annotations

import functools
import inspect
import re
import traceback
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import nullcontext
from typing import Annotated, Any, ClassVar, TypeVar

from lilya import status
from lilya._internal._events import AsyncLifespan, handle_lifespan_events
from lilya._internal._middleware import wrap_middleware
from lilya._internal._module_loading import import_string
from lilya._internal._path import (
    clean_path,
    compile_path,
    get_route_path,
    parse_path,
    replace_params,
)
from lilya._internal._permissions import wrap_permission
from lilya._internal._responses import BaseHandler
from lilya._internal._urls import include
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.conf import _monkay
from lilya.conf.global_settings import Settings
from lilya.datastructures import URL, Header, ScopeHandler, SendReceiveSniffer, URLPath
from lilya.enums import EventType, HTTPMethod, Match, ScopeType
from lilya.exceptions import ContinueRouting, HTTPException, ImproperlyConfigured
from lilya.middleware.base import DefineMiddleware
from lilya.permissions.base import DefinePermission
from lilya.requests import Request
from lilya.responses import PlainText, RedirectResponse, Response
from lilya.types import (
    ASGIApp,
    Dependencies,
    Doc,
    ExceptionHandler,
    Lifespan,
    Receive,
    Scope,
    Send,
)
from lilya.websockets import WebSocket, WebSocketClose

T = TypeVar("T")


class PathHandler(ScopeHandler):
    """
    Represents a route handler that handles incoming requests.

    Args:
        child_scope (Scope): The child scope of the handler.
        scope (Scope): The scope of the handler.
        sniffer (SendReceiveSniffer): The Sniffer.

    Attributes:
        child_scope (Scope): The child scope of the handler.
        scope (Scope): The scope of the handler.
        receive (Receive): The receive function for handling incoming messages.
        send (Send): The send function for sending messages.
        sniffer (SendReceiveSniffer): The Sniffer.
    """

    def __init__(self, child_scope: Scope, scope: Scope, sniffer: SendReceiveSniffer) -> None:
        super().__init__(scope=scope, receive=sniffer.receive, send=sniffer.send)
        self.child_scope = child_scope
        self.sniffer = sniffer


class NoMatchFound(Exception):
    """
    Raised by `.path_for(name, **path_params)` and `.path_for(name, **path_params)`
    if no matching route exists.
    """

    def __init__(self, name: str, path_params: dict[str, Any]) -> None:
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


class PassPartialMatches(BaseException):
    """
    Signals that the route handling should continue and not stop with the current route
    and partial matches should be transfered
    """

    partial_matches: Sequence[tuple[BaseRouter, BasePath, PathHandler]] = ()

    def __init__(
        self, *, partial_matches: Sequence[tuple[BaseRouter, BasePath, PathHandler]]
    ) -> None:
        self.partial_matches = partial_matches


def get_name(handler: Callable[..., Any]) -> str:
    """
    Returns the name of a given handler.
    """
    if hasattr(handler, "func"):
        handler = handler.func

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

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches for a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Returns a URL of a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def url_for(self, name: str, /, **path_params: Any) -> URLPath:
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

    @staticmethod
    async def handle_not_found_fallthrough(scope: Scope, receive: Receive, send: Send) -> None:
        raise ContinueRouting()

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

    async def handle_exception_handlers(
        self, scope: Scope, receive: Receive, send: Send, exc: Exception
    ) -> None:
        """
        Manages exception handlers for HTTP and WebSocket scopes.

        Args:
            scope (dict): The ASGI scope.
            receive (callable): The receive function.
            send (callable): The send function.
            exc (Exception): The exception to handle.
        """
        status_code = self._get_status_code(exc)

        if scope["type"] == ScopeType.HTTP:
            await self._handle_http_exception(scope, receive, send, exc, status_code)
        elif scope["type"] == ScopeType.WEBSOCKET:
            await self._handle_websocket_exception(send, exc, status_code)

    def _get_status_code(self, exc: Exception) -> int:
        """
        Get the status code from the exception.

        Args:
            exc (Exception): The exception.

        Returns:
            int: The status code.
        """
        return getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def _handle_http_exception(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        exc: Exception,
        status_code: int,
    ) -> None:
        """
        Handle HTTP exceptions.

        Args:
            scope (dict): The ASGI scope.
            receive (callable): The receive function.
            send (callable): The send function.
            exc (Exception): The exception to handle.
            status_code (int): The status code.
        """
        exception_handler = self.exception_handlers.get(
            status_code
        ) or self.exception_handlers.get(exc.__class__)

        if exception_handler is None:
            raise exc

        request = Request(scope=scope, receive=receive, send=send)
        response = exception_handler(request, exc)
        await response(scope=scope, receive=receive, send=send)

    async def _handle_websocket_exception(
        self, send: Send, exc: Exception, status_code: int
    ) -> None:
        """
        Handle WebSocket exceptions.

        Args:
            send (callable): The send function.
            exc (Exception): The exception to handle.
            status_code (int): The status code.
        """
        reason = repr(exc)
        await send({"type": "websocket.close", "code": status_code, "reason": reason})

    @property
    def stringify_parameters(self) -> list[str]:  # pragma: no cover
        """
        Gets the param:type in string like list.
        Used for the directive `lilya show-urls`.
        """
        path_components = parse_path(self.path)
        parameters = [component for component in path_components if isinstance(component, tuple)]
        stringified_parameters = [f"{param.name}:{param.type}" for param in parameters]
        return stringified_parameters


class Path(BaseHandler, BasePath):
    """
    The way you can define a route in Lilya and apply the corresponding
    path definition.

    ## Example

    ```python
    from lilya.routing import Path

    Path("/home", callable=..., name="home")
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
        "exception_handlers",
        "deprecated",
        "before_request",
        "after_request",
        "__handler_app__",
        "_signature",
        "dependencies",
    )

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
        deprecated: bool = False,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = clean_path(path)
        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.methods: list[str] | None = methods
        self.deprecated = deprecated
        self.dependencies = dependencies if dependencies is not None else {}

        # Defition of the app
        self.__handler_app__ = handler
        while isinstance(self.__handler_app__, functools.partial):
            self.__handler_app__ = self.__handler_app__.func

        if inspect.isfunction(self.__handler_app__) or inspect.ismethod(self.__handler_app__):
            self.app = self.handle_response(handler)
            if methods is None:
                self.methods = [HTTPMethod.GET.value]
        else:
            self.app = handler

        if middleware is not None:
            self.middleware = [wrap_middleware(mid) for mid in middleware]
        else:
            self.middleware = middleware if middleware is not None else []

        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        # Controllers are an exception, they can have permissions and middlewares
        # applied to the class level
        self._apply_controller_options()

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

        if self.methods is not None:
            self.methods = [method.upper() for method in self.methods]
            if HTTPMethod.GET in self.methods:
                self.methods.append(HTTPMethod.HEAD.value)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    @property
    def signature(self) -> inspect.Signature:
        if not hasattr(self, "_signature"):
            self._signature: inspect.Signature = inspect.signature(self.__handler_app__)
            self.handle_signature()
        return self._signature

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not _monkay.settings.enforce_return_annotation:
            return None

        if self.signature.return_annotation is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated. "
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )

    def _apply_controller_options(self) -> None:
        """
        Apply controller options to the path.
        """
        if hasattr(self.app, "__is_controller__"):
            controller = self.app
            if controller.permissions:
                self.wrapped_permissions.extend(
                    [wrap_permission(permission) for permission in controller.permissions]
                )

            if controller.middleware:
                self.middleware.extend([wrap_middleware(mid) for mid in controller.middleware])

            if controller.exception_handlers:
                self.exception_handlers.update(controller.exception_handlers)

            if controller.dependencies:
                self.dependencies.update(controller.dependencies)

            if controller.before_request:
                self.before_request.extend(controller.before_request)

            if controller.after_request:
                self.after_request.extend(controller.after_request)

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

    def url_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.path_for(name, **path_params)

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

    def handle_match(self, scope: Scope, match: re.Match) -> tuple[Match, Scope]:
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

        upstream = list(scope.get("dependencies", []))
        child_scope = {
            "handler": self.handler,
            "path_params": path_params,
            "dependencies": upstream + [self.dependencies],
        }

        if self.methods and scope["method"] not in self.methods:
            return Match.PARTIAL, child_scope
        else:
            return Match.FULL, child_scope

    async def handle_controller(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Instantiates the Controller object and executes
        the call.
        """
        app = self.app()  # type: ignore[call-arg]
        await app(scope, receive, send)  # type: ignore

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
            try:
                for before_request in self.before_request:
                    if inspect.isclass(before_request):
                        before_request = before_request()

                    if is_async_callable(before_request):
                        await before_request(scope, receive, send)
                    else:
                        await run_in_threadpool(before_request, scope, receive, send)

                if not hasattr(self.app, "__is_controller__"):
                    await self.app(scope, receive, send)
                else:
                    await self.handle_controller(scope, receive, send)

                for after_request in self.after_request:
                    if inspect.isclass(after_request):
                        after_request = after_request()

                    if is_async_callable(after_request):
                        await after_request(scope, receive, send)
                    else:
                        await run_in_threadpool(after_request, scope, receive, send)

            except Exception as ex:
                await self.handle_exception_handlers(scope, receive, send, ex)

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
        "exception_handlers",
        "before_request",
        "after_request",
        "__handler_app__",
        "_signature",
        "dependencies",
    )

    def __init__(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        name: str | None = None,
        include_in_schema: bool = True,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> None:
        assert path.startswith("/"), "Paths must start with '/'"
        self.path = clean_path(path)

        self.handler = handler
        self.name = get_name(handler) if name is None else name
        self.include_in_schema = include_in_schema
        self.dependencies = dependencies if dependencies is not None else {}

        # Defition of the app
        self.__handler_app__ = handler
        while isinstance(self.__handler_app__, functools.partial):
            self.__handler_app__ = self.__handler_app__.func

        if inspect.isfunction(self.__handler_app__) or inspect.ismethod(self.__handler_app__):
            self.app = self.handle_websocket_session(handler)
        else:
            self.app = handler

        if middleware is not None:
            self.middleware = [wrap_middleware(mid) for mid in middleware]
        else:
            self.middleware = middleware or []

        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        self._apply_controller_options()

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

        self.path_regex, self.path_format, self.param_convertors, self.path_start = compile_path(
            self.path
        )

    @property
    def signature(self) -> inspect.Signature:
        if not hasattr(self, "_signature"):
            self._signature: inspect.Signature = inspect.signature(self.__handler_app__)
            self.handle_signature()
        return self._signature

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not _monkay.settings.enforce_return_annotation:
            return None

        if self.signature.return_annotation is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated. "
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )

    def _apply_controller_options(self) -> None:
        """
        Apply controller options to the path.
        """
        if hasattr(self.app, "__is_controller__"):
            controller = self.app
            if controller.permissions:
                self.wrapped_permissions.extend(
                    [wrap_permission(permission) for permission in controller.permissions]
                )

            if controller.middleware:
                self.middleware.extend([wrap_middleware(mid) for mid in controller.middleware])

            if controller.exception_handlers:
                self.exception_handlers.update(controller.exception_handlers)

            if controller.dependencies and self.dependencies:
                self.dependencies.update(controller.dependencies)

            if controller.before_request:
                self.before_request.extend(controller.before_request)

            if controller.after_request:
                self.after_request.extend(controller.after_request)

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

    def handle_match(self, scope: Scope, match: re.Match) -> tuple[Match, Scope]:
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
        upstream = list(scope.get("dependencies", []))
        child_scope = {
            "handler": self.handler,
            "path_params": path_params,
            "dependencies": upstream + [self.dependencies],
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

    def path_for(self, name: str, **path_params: Any) -> URLPath:
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

    def url_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.path_for(name, **path_params)

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


class Host(BasePath):
    __slots__ = (
        "host",
        "app",
        "__base_app__",
        "name",
        "middleware",
        "permissions",
        "exception_handlers",
        "before_request",
        "after_request",
    )

    def __init__(
        self,
        host: str,
        app: ASGIApp,
        name: str | None = None,
        *,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> None:
        assert not host.startswith("/"), "Host must not start with '/'"
        self.host = host
        self.app = self.__base_app__ = app
        self.name = name
        self.host_regex, self.host_format, self.param_convertors, self.path_start = compile_path(
            host
        )
        self.middleware = middleware if middleware is not None else []
        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

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
            headers = Header.ensure_header_instance(scope=scope)
            host = headers.get("host", "").split(":")[0]
            match = self.host_regex.match(host)
            if match:
                return self.handle_match(scope, match)

        return Match.NONE, {}

    def handle_match(self, scope: Scope, match: re.Match) -> tuple[Match, Scope]:
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

    def url_for_with_name(self, path_params: dict) -> URLPath:
        return self.path_for_with_name(path_params)

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

    def url_for_without_name(self, name: str, /, **path_params: Any) -> URLPath:
        return self.path_for_without_name(name, path_params)

    def __repr__(self) -> str:
        name = self.name or ""
        return f"{self.__class__.__name__}(host={self.host!r}, name={name!r}, app={self.app!r})"


class BaseRouter:
    """
    A Lilya base router object.
    """

    __slots__ = (
        "routes",
        "redirect_slashes",
        "default",
        "on_startup",
        "on_shutdown",
        "middleware",
        "permissions",
        "include_in_schema",
        "deprecated",
        "lifespan_context",
        "middleware_stack",
        "permission_started",
        "settings_module",
        "is_sub_router",
        "before_request",
        "after_request",
        "dependencies",
    )

    def __init__(
        self,
        routes: Sequence[BasePath] | None = None,
        redirect_slashes: bool = True,
        default: ASGIApp | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
        lifespan: Lifespan[Any] | None = None,
        *,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
        settings_module: Annotated[
            Settings | None,
            Doc(
                """
                Alternative settings parameter. This parameter is an alternative to
                `LILYA_SETTINGS_MODULE` way of loading your settings into a Lilya application.

                When the `settings_module` is provided, it will make sure it takes priority over
                any other settings provided for the instance.
                """
            ),
        ] = None,
        include_in_schema: bool = True,
        deprecated: bool = False,
        is_sub_router: bool = False,
    ) -> None:
        assert lifespan is None or (on_startup is None and on_shutdown is None), (
            "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."
        )

        if inspect.isasyncgenfunction(lifespan) or inspect.isgeneratorfunction(lifespan):
            raise ImproperlyConfigured(
                "async function generators are not allowed. Use @contextlib.asynccontextmanager instead."
            )

        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.dependencies = dependencies if dependencies is not None else {}

        self.lifespan_context = handle_lifespan_events(
            on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan
        )

        if self.lifespan_context is None:
            self.lifespan_context = AsyncLifespan(self)

        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.handle_not_found if default is None else default
        self.include_in_schema = include_in_schema
        self.deprecated = deprecated

        self.middleware = middleware if middleware is not None else []
        self.permissions = permissions if permissions is not None else []
        self.settings_module = settings_module
        self.middleware_stack = self.app
        self.permission_started = False
        self.is_sub_router = is_sub_router

        self.before_request = before_request if before_request is not None else []
        self.after_request = after_request if after_request is not None else []

        self.wrapped_permissions = [
            wrap_permission(permission) for permission in permissions or []
        ]

        self._apply_permissions(self.wrapped_permissions)
        self._apply_middleware(self.middleware)

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
                self.middleware_stack = cls(app=self.middleware_stack, *args, **options)

    def _apply_permissions(self, permissions: Sequence[DefinePermission] | None) -> None:
        """
        Apply permissions to the app.

        Args:
            permissions (Union[Sequence[DefinePermission], None]): The permissions.

        Returns:
            None
        """
        if permissions is not None:
            for cls, args, options in reversed(self.permissions):
                self.middleware_stack = cls(app=self.middleware_stack, *args, **options)

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        for route in self.routes:
            try:
                return route.path_for(name, **path_params)
            except NoMatchFound:
                ...
        raise NoMatchFound(name, path_params)

    def url_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.path_for(name, **path_params)

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

    async def handle_route(self, route: BasePath, path_handler: PathHandler) -> None:
        """
        Handle a route match.

        Args:
            route: The matched route.
            path_handler (PathHandler): The PathHandler.
        """
        new_scope = dict(path_handler.scope)
        new_scope.update(path_handler.child_scope)
        await route.handle_dispatch(new_scope, path_handler.receive, path_handler.send)  # type: ignore

    async def handle_partial(self, route: BasePath, path_handler: PathHandler) -> None:
        """
        Handle a partial route match.

        Args:
            route: The matched route.
            path_handler (PathHandler): The PathHandler.
        """
        new_scope = dict(path_handler.scope)
        new_scope.update(path_handler.child_scope)
        await route.handle_dispatch(new_scope, path_handler.receive, path_handler.send)  # type: ignore

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
        assert scope["type"] in (
            ScopeType.HTTP,
            ScopeType.WEBSOCKET,
            ScopeType.LIFESPAN,
        )

        if "router" not in scope:
            scope["router"] = self

        sniffer = SendReceiveSniffer(receive, send)

        partial_matches: list[tuple[BaseRouter, BasePath, PathHandler]] = []
        had_match = False

        for route in self.routes:
            # we cannot continue when the sniffer detects a sent
            if sniffer.sent:
                return
            match, child_scope = route.search(scope)
            if match == Match.NONE:
                continue
            had_match = True
            path_handler = PathHandler(child_scope=child_scope, scope=scope, sniffer=sniffer)
            try:
                if match == Match.FULL:
                    await self.handle_route(route, path_handler=path_handler)
                    if sniffer.sent:
                        return  # type: ignore
                    else:
                        sniffer.repeat_message = True
                elif match == Match.PARTIAL:
                    partial_matches.append((self, route, path_handler))
            except PassPartialMatches as exc:
                # collect the partial matches from the sub-router
                partial_matches.extend(exc.partial_matches)
            except ContinueRouting:
                assert not sniffer.sent, "Cannot continue routing when an answer was already sent."
                sniffer.repeat_message = True
        # check if redirect would be possible, when no match was found
        if not had_match and self.redirect_slashes:
            route_path = get_route_path(scope)
            if scope["type"] == ScopeType.HTTP and route_path != "/":
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

        if self.is_sub_router:
            # now pass the partial matches to the upper router
            raise PassPartialMatches(partial_matches=partial_matches)
        # when in the main router, check partial matches (method does not match)
        # use for this the handler method of the sub-router to keep their modifications
        for router, route, path_handler in partial_matches:
            try:
                await router.handle_partial(route, path_handler)
                # should propagate back to this sniffer
                if sniffer.sent:
                    return
                else:
                    # rearm sniffer of the path handler (sub router)
                    path_handler.sniffer.repeat_message = True
                    sniffer.repeat_message = True
            except ContinueRouting:
                assert not sniffer.sent, "Cannot continue routing when an answer was already sent."
                path_handler.sniffer.repeat_message = True
                sniffer.repeat_message = True

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
        if "app" in scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

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
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        namespace: str | None = None,
        pattern: str | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
        redirect_slashes: bool = True,
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
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            namespace=namespace,
            pattern=pattern,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
            redirect_slashes=redirect_slashes,
        )
        self.routes.append(route)

    def host(self, host: str, app: ASGIApp, name: str | None = None) -> None:
        """
        Adds a Host application into the routes.
        """
        route = Host(host, app=app, name=name)
        self.routes.append(route)

    def add_route(
        self,
        path: str,
        handler: Callable[[Request], Awaitable[Response] | Response] | Any,
        methods: list[str] | None = None,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
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
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            name=name,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )
        self.routes.append(route)

    def add_websocket_route(
        self,
        path: str,
        handler: Callable[[WebSocket], Awaitable[None]],
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> None:
        """
        Manually creates a `WebSocketPath` from a given handler.
        """
        route = WebSocketPath(
            path,
            handler=handler,
            middleware=middleware,
            permissions=permissions,
            name=name,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            before_request=before_request,
            after_request=after_request,
        )
        self.routes.append(route)

    def add_event_handler(
        self, event_type: str, func: Callable[[], Any]
    ) -> None:  # pragma: no cover
        assert event_type in (
            EventType.ON_STARTUP,
            EventType.ON_SHUTDOWN,
            EventType.STARTUP,
            EventType.SHUTDOWN,
        )

        if event_type in (EventType.ON_STARTUP, EventType.STARTUP):
            self.on_startup.append(func)
        else:
            self.on_shutdown.append(func)

    def on_event(self, event_type: str) -> Callable:
        def wrapper(func: Callable) -> Callable:
            self.add_event_handler(event_type, func)
            return func

        return wrapper

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ctxmanager = (
            nullcontext()
            if self.settings_module is None
            else _monkay.with_settings(self.settings_module)
        )
        with ctxmanager:
            if scope["type"] == ScopeType.LIFESPAN:
                await self.lifespan(scope, receive, send)
                return

            for before_request in self.before_request:
                if inspect.isclass(before_request):
                    before_request = before_request()

                if is_async_callable(before_request):
                    await before_request(scope, receive, send)
                else:
                    await run_in_threadpool(before_request, scope, receive, send)
            await self.middleware_stack(scope, receive, send)

            for after_request in self.after_request:
                if inspect.isclass(after_request):
                    after_request = after_request()

                if is_async_callable(after_request):
                    await after_request(scope, receive, send)
                else:
                    await run_in_threadpool(after_request, scope, receive, send)


class RoutingMethodsMixin:
    def get(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a GET route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="GET",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def head(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a HEAD route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="HEAD",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def post(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a POST route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="POST",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def put(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a PUT route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="PUT",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def patch(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a PATCH route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="PATCH",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def delete(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a DELETE route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="DELETE",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def trace(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a TRACE route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="TRACE",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def options(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a OPTIONS route.

        Args:
            path (str): The URL path pattern for the route.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        return self.forward_single_method_route(
            path=path,
            method="OPTIONS",
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def forward_single_method_route(
        self,
        path: str,
        method: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """For customization, defaults to route."""
        return self.route(
            path=path,
            methods=[method],
            name=name,
            middleware=middleware,
            permissions=permissions,
            exception_handlers=exception_handlers,
            dependencies=dependencies,
            include_in_schema=include_in_schema,
            before_request=before_request,
            after_request=after_request,
        )

    def route(
        self,
        path: str,
        methods: list[str],
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a generic route.

        Args:
            path (str): The URL path pattern for the route.
            methods (list[str] | None, optional): The HTTP methods allowed for the route. Defaults to None.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        raise NotImplementedError()

    def websocket(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a WebSocket route.

        Args:
            path (str): The URL path for the WebSocket route.
            name (str, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware], optional): The middleware to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission], optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler], optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """
        raise NotImplementedError()


class Router(RoutingMethodsMixin, BaseRouter):
    """
    Contains all the needed base routing system and adds the ability to use decorators.
    """

    def route(
        self,
        path: str,
        methods: list[str],
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        include_in_schema: bool = True,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a generic route.

        Args:
            path (str): The URL path pattern for the route.
            methods (list[str] | None, optional): The HTTP methods allowed for the route. Defaults to None.
            name (str | None, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware] | None, optional): The middleware functions to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission] | None, optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler] | None, optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            include_in_schema (bool, optional): Whether to include the route in the API schema. Defaults to True.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.
        """

        def wrapper(func: Callable) -> Callable:
            self.add_route(
                path=path,
                handler=func,
                methods=methods,
                name=name,
                middleware=middleware,
                permissions=permissions,
                exception_handlers=exception_handlers,
                dependencies=dependencies,
                include_in_schema=include_in_schema,
                before_request=before_request,
                after_request=after_request,
            )
            func._lilya_dependencies = dependencies or {}
            return func

        return wrapper

    def websocket(
        self,
        path: str,
        name: str | None = None,
        middleware: Sequence[DefineMiddleware] | None = None,
        permissions: Sequence[DefinePermission] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        dependencies: Dependencies | None = None,
        before_request: Sequence[Callable[..., Any]] | None = None,
        after_request: Sequence[Callable[..., Any]] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator for defining a WebSocket route.

        Args:
            path (str): The URL path for the WebSocket route.
            name (str, optional): The name of the route. Defaults to None.
            middleware (Sequence[DefineMiddleware], optional): The middleware to apply to the route. Defaults to None.
            permissions (Sequence[DefinePermission], optional): The permissions required for the route. Defaults to None.
            exception_handlers (Mapping[Any, ExceptionHandler], optional): The exception handlers for the route. Defaults to None.
            dependencies (Dependencies | None, optional): Dependencies to inject into the route handler. Defaults to None.
            before_request (Sequence[Callable[..., Any]] | None, optional): Functions to run before the request is processed. Defaults to None.
            after_request (Sequence[Callable[..., Any]] | None, optional): Functions to run after the request is processed. Defaults to None.

        Returns:
            Callable[..., Any]: The decorated function.

        """

        def wrapper(func: Callable) -> Callable:
            self.add_websocket_route(
                path=path,
                handler=func,
                name=name,
                middleware=middleware,
                permissions=permissions,
                exception_handlers=exception_handlers,
                dependencies=dependencies,
                before_request=before_request,
                after_request=after_request,
            )
            func._lilya_dependencies = dependencies or {}
            return func

        return wrapper


# Declare an alias for the Path
RoutePath = Path


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

        self.middleware = middleware if middleware is not None else []
        self.permissions = permissions if permissions is not None else []
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)

        if dependencies is None and hasattr(self.__base_app__, "dependencies"):
            self.dependencies = self.__base_app__.dependencies or {}
        else:
            self.dependencies = dependencies or {}

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

    def url_for(self, name: str, /, **path_params: Any) -> URLPath:
        return self.path_for(name, **path_params)

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
