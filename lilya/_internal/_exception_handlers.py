from __future__ import annotations

from json import loads
from typing import Dict, Type, cast

from lilya import status
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.enums import ScopeType
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.types import (
    ASGIApp,
    ExceptionHandler,
    HTTPExceptionHandler,
    Message,
    Receive,
    Scope,
    Send,
    WebSocketExceptionHandler,
)
from lilya.websockets import WebSocket

ExceptionHandlers = Dict[Type[Exception], ExceptionHandler]
StatusHandlers = Dict[int, ExceptionHandler]


def _lookup_exception_handler(
    exc_handlers: ExceptionHandlers, exc: Exception
) -> ExceptionHandler | None:
    """
    Looks up an exception handler for a given exception type in the exception handlers dictionary.

    Args:
        exc_handlers (ExceptionHandlers): Dictionary of exception handlers.
        exc (Exception): The exception for which to find a handler.

    Returns:
        ExceptionHandler | None: The found exception handler or None if not found.
    """
    for cls in type(exc).__mro__:
        if cls in exc_handlers:
            return exc_handlers[cls]
    return None


def wrap_app_handling_exceptions(app: ASGIApp, conn: Request | WebSocket) -> ASGIApp:
    """
    Wraps an ASGI application, handling exceptions and applying exception handlers.

    Args:
        app (ASGIApp): The original ASGI application.
        conn (Union[Request, WebSocket]): The connection object (Request or WebSocket).

    Returns:
        ASGIApp: The wrapped ASGI application.
    """
    try:
        exception_handlers, status_handlers = conn.scope["lilya.exception_handlers"]
    except KeyError:
        exception_handlers, status_handlers = {}, {}

    async def wrapped_app(scope: Scope, receive: Receive, send: Send) -> None:
        """
        Wrapper function for the ASGI application, handling exceptions and applying handlers.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        response_started = False

        async def sender(message: Message) -> None:
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await app(scope, receive, sender)
        except Exception as exc:
            handler = None

            if isinstance(exc, HTTPException):
                handler = status_handlers.get(exc.status_code)

            if handler is None:
                handler = _lookup_exception_handler(exception_handlers, exc)

            if handler is None:
                raise exc

            if response_started:
                msg = "Caught handled exception, but response already started."
                raise RuntimeError(msg) from exc

            await handle_exception(scope, conn, exc, handler)

    return wrapped_app


async def handle_exception(
    scope: Scope, conn: Request | WebSocket, exc: Exception, handler: ExceptionHandler
) -> None:
    """
    Handles an exception by applying the specified exception handler.

    Args:
        scope (Scope): The request scope.
        conn (Union[Request, WebSocket]): The connection object (Request or WebSocket).
        exc (Exception): The exception to handle.
        handler (ExceptionHandler): The exception handler.

    Returns:
        None
    """
    if scope["type"] == ScopeType.HTTP:
        await handle_http_exception(cast(Request, conn), exc, handler)
    elif scope["type"] == ScopeType.WEBSOCKET:
        await handle_websocket_exception(cast(WebSocket, conn), exc, handler)


async def handle_http_exception(
    conn: Request, exc: Exception, handler: HTTPExceptionHandler
) -> None:
    """
    Handles an HTTP exception by applying the specified HTTP exception handler.

    Args:
        conn (Request): The HTTP request object.
        exc (Exception): The exception to handle.
        handler (HTTPExceptionHandler): The HTTP exception handler.

    Returns:
        None
    """
    if is_async_callable(handler):
        response = await handler(conn, exc)
    else:
        response = await run_in_threadpool(handler, conn, exc)
    await response(conn.scope, conn.receive, conn.send)


async def handle_websocket_exception(
    conn: WebSocket, exc: Exception, handler: WebSocketExceptionHandler
) -> None:
    """
    Handles a WebSocket exception by applying the specified WebSocket exception handler.

    Args:
        conn (WebSocket): The WebSocket connection object.
        exc (Exception): The exception to handle.
        handler (WebSocketExceptionHandler): The WebSocket exception handler.

    Returns:
        None
    """
    if is_async_callable(handler):
        await handler(conn, exc)
    else:
        await run_in_threadpool(handler, conn, exc)


async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    status_code = status.HTTP_400_BAD_REQUEST
    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
    return JSONResponse({"detail": details}, status_code=status_code)
