from __future__ import annotations

import html
import inspect
import traceback
from collections.abc import Callable
from typing import Any

from lilya import status
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.enums import MediaType, ScopeType
from lilya.middleware.styles.errors import (
    get_center_line,
    get_css_style,
    get_frame,
    get_js,
    get_line,
    get_template_errors,
)
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.responses import HTMLResponse, PlainText, Response
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class ServerErrorMiddleware(MiddlewareProtocol):
    """
    Middleware for handling server errors and returning appropriate 500 responses.

    If 'debug' is set, traceback responses will be returned;
    otherwise, the designated 'handler' will be called.
    """

    def __init__(
        self,
        app: ASGIApp,
        handler: Callable[[Request, Exception], Any] | None = None,
        debug: bool = False,
    ) -> None:
        """
        Initialize the ServerErrorMiddleware.

        Args:
            app (ASGIApp): The ASGI application.
            handler (Optional[Callable]): Custom error handler.
            debug (bool): Enable debug mode for returning traceback responses.
        """
        self.app = app
        self.handler = handler
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle incoming ASGI scope.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive function.
            send (Send): ASGI send function.
        """
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send

            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            request = Request(scope)
            response = await self.handle_exception(request, exc, scope, receive, send)
            await self.send_response(response, scope, receive, send, response_started)
            raise exc

    async def handle_exception(
        self, request: Request, exc: Exception, scope: Scope, receive: Receive, send: Send
    ) -> Any:
        """
        Handle the exception and return an appropriate response.

        Args:
            request (Request): The incoming HTTP request.
            exc (Exception): The raised exception.
            scope (Scope): The ASGI scope.
            receive (Receive): ASGI receive function.
            send (Send): ASGI send function.

        Returns:
            The appropriate HTTP response.
        """
        if self.debug:
            return self.debug_response(request, exc)
        elif self.handler is None:
            return self.error_response(request, exc)
        else:
            return await self.run_handler(request, exc)

    async def run_handler(self, request: Request, exc: Exception) -> Any:
        """
        Run the custom error handler.

        Args:
            request (Request): The incoming HTTP request.
            exc (Exception): The raised exception.

        Returns:
            The response generated by the custom error handler.
        """
        if is_async_callable(self.handler):
            return await self.handler(request, exc)
        else:
            return await run_in_threadpool(self.handler, request, exc)

    async def send_response(
        self,
        response: Response,
        scope: Scope,
        receive: Receive,
        send: Send,
        response_started: bool,
    ) -> None:
        """
        Send the generated response.

        Args:
            response (Response): The HTTP response to send.
            scope (Scope): The ASGI scope.
            receive (Receive): ASGI receive function.
            send (Send): ASGI send function.
        """
        if not response_started:
            await response(scope, receive, send)

    def error_response(self, request: Request, exc: Exception) -> Response:
        """
        Generate a plain text 500 error response.

        Args:
            request (Request): The incoming HTTP request.
            exc (Exception): The raised exception.

        Returns:
            Response: The plain text 500 error response.
        """
        return PlainText(
            "Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def debug_response(self, request: Request, exc: Exception) -> Response:
        """
        Generate a debug response with HTML or plain text.

        Args:
            request (Request): The incoming HTTP request.
            exc (Exception): The raised exception.

        Returns:
            Response: The debug response.
        """
        accept = request.headers.get("accept", "")

        if MediaType.HTML in accept:
            content = self.generate_html(exc)
            return HTMLResponse(content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        content = self.generate_plain_text(exc)
        return PlainText(content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_html(self, exc: Exception) -> str:
        """
        Generate HTML content for the debug response.

        Args:
            exc (Exception): The raised exception.

        Returns:
            str: The HTML content.
        """
        traceback_obj = traceback.TracebackException.from_exception(exc, capture_locals=True)

        exc_html = ""
        is_collapsed = False
        exc_traceback = exc.__traceback__
        if exc_traceback is not None:
            frames = inspect.getinnerframes(exc_traceback, 7)
            for frame in reversed(frames):
                exc_html += self.generate_frame_html(frame, is_collapsed)
                is_collapsed = True

        # escape error class and text
        try:
            exc_type_str = traceback_obj.exc_type_str
        except Exception:
            # for older python versions < 3.13
            exc_type_str = traceback_obj.exc_type.__name__
        error = f"{html.escape(exc_type_str)}: {html.escape(str(traceback_obj))}"

        template = get_template_errors()
        return template.format(styles=get_css_style(), js=get_js(), error=error, exc_html=exc_html)

    def generate_plain_text(self, exc: Exception) -> str:
        """
        Generate plain text content for the debug response.

        Args:
            exc (Exception): The raised exception.

        Returns:
            str: The plain text content.
        """
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    def format_line(self, index: int, line: str, frame_lineno: int, frame_index: int) -> str:
        """
        Format a single line in a traceback frame.

        Args:
            index (int): The index of the line.
            line (str): The content of the line.
            frame_lineno (int): Line number in the frame.
            frame_index (int): Index of the frame.

        Returns:
            str: The formatted line HTML.
        """
        escaped_line = html.escape(line).replace(" ", "&nbsp")
        lineno = (frame_lineno - frame_index) + index

        values = {
            "line": escaped_line,
            "lineno": lineno,
        }

        return (
            get_line().format(**values)
            if index != frame_index
            else get_center_line().format(**values)
        )

    def generate_frame_html(self, frame: inspect.FrameInfo, is_collapsed: bool) -> str:
        """
        Generate HTML content for a single frame in the traceback.

        Args:
            frame (FrameInfo): Information about the frame.
            is_collapsed (bool): Whether the frame is collapsed.

        Returns:
            str: The HTML content for the frame.
        """
        code_context = "".join(
            self.format_line(
                index,
                line,
                frame.lineno,
                frame.index,
            )
            for index, line in enumerate(frame.code_context or [])
        )

        values = {
            "frame_filename": html.escape(frame.filename),
            "frame_lineno": frame.lineno,
            "frame_name": html.escape(frame.function),
            "code_context": code_context,
            "collapsed": "collapsed" if is_collapsed else "",
            "collapse_button": "+" if is_collapsed else "&#8210;",
        }
        return get_frame().format(**values)
