from __future__ import annotations

from typing import Any, Callable, Mapping

from lilya import status
from lilya._internal._exception_handlers import (
    ExceptionHandlers,
    StatusHandlers,
    wrap_app_handling_exceptions,
)
from lilya.enums import ScopeType
from lilya.exceptions import HTTPException, WebSocketException
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.responses import PlainText, Response
from lilya.types import ASGIApp, Receive, Scope, Send
from lilya.websockets import WebSocket


class ExceptionMiddleware(MiddlewareProtocol):
    """
    Middleware for handling exceptions in an ASGI application.

    This middleware allows registering custom exception handlers and status code handlers.

    Args:
        app (ASGIApp): The ASGI application.
        handlers (Optional[Mapping]): Custom exception handlers.
        debug (bool): Enable debug mode for handling 404 cases.

    Usage:
    ```python
    app = ExceptionMiddleware(app, handlers={404: custom_handler}, debug=True)
    ```

    """

    def __init__(
        self,
        app: ASGIApp,
        handlers: Mapping[Any, Callable[[Request, Exception], Response]] | None = None,
        debug: bool = False,
    ) -> None:
        self.app = app
        self.debug = debug
        self._status_handlers: StatusHandlers = {}
        self._exception_handlers: ExceptionHandlers = {
            HTTPException: self.http_exception,
            WebSocketException: self.websocket_exception,
        }
        if handlers is not None:
            self._add_handlers(handlers)

    def _add_handlers(
        self, handlers: Mapping[Any, Callable[[Request, Exception], Response]]
    ) -> None:
        for key, value in handlers.items():
            if isinstance(key, int):
                self._status_handlers[key] = value
            else:
                assert issubclass(key, Exception)
                self._exception_handlers[key] = value

    def add_exception_handler(
        self,
        exception_or_status: type[Exception] | int,
        handler: Callable[[Request, Exception], Response],
    ) -> None:
        """
        Add a custom exception handler.

        Args:
            exception_or_status (Union[Type[Exception], int]): Exception class or status code.
            handler (Callable[[Request, Exception], Response]): Exception handler function.

        Usage:
        ```python
        app.add_exception_handler(404, custom_handler)
        ```

        """
        if isinstance(exception_or_status, int):
            self._status_handlers[exception_or_status] = handler
        else:
            assert issubclass(exception_or_status, Exception)
            self._exception_handlers[exception_or_status] = handler

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle incoming ASGI scope.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive function.
            send (Send): ASGI send function.

        """
        if scope["type"] not in (ScopeType.HTTP, ScopeType.WEBSOCKET):
            await self.app(scope, receive, send)
            return

        scope["lilya.exception_handlers"] = (
            self._exception_handlers,
            self._status_handlers,
        )

        connection = self._get_connection(scope, receive, send)
        await wrap_app_handling_exceptions(self.app, connection)(scope, receive, send)

    def _get_connection(self, scope: Scope, receive: Receive, send: Send) -> Request | WebSocket:
        """
        Get the appropriate connection object based on the ASGI scope type.

        Args:
            scope (Scope): ASGI scope.

        Returns:
            Union[Request, WebSocket]: Connection object.

        """
        if scope["type"] == ScopeType.HTTP:
            return Request(scope, receive, send)
        return WebSocket(scope, receive, send)

    def http_exception(self, request: Request, exc: Exception) -> Response:
        """
        Handle HTTP exceptions.

        Args:
            request (Request): HTTP request.
            exc (Exception): HTTP exception.

        Returns:
            Response: HTTP response.

        """
        assert isinstance(exc, HTTPException)
        if exc.status_code in {status.HTTP_204_NO_CONTENT, status.HTTP_304_NOT_MODIFIED}:
            return Response(status_code=exc.status_code, headers=exc.headers)
        return PlainText(exc.detail, status_code=exc.status_code, headers=exc.headers)

    async def websocket_exception(self, websocket: WebSocket, exc: Exception) -> None:
        """
        Handle WebSocket exceptions.

        Args:
            websocket (WebSocket): WebSocket connection.
            exc (Exception): WebSocket exception.

        """
        assert isinstance(exc, WebSocketException)
        await websocket.close(code=exc.code, reason=exc.reason)
