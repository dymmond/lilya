from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

from lilya._internal._module_loading import import_string
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.types import Scope

if TYPE_CHECKING:
    from lilya.apps import Lilya

try:
    from a2wsgi.wsgi import WSGIMiddleware as A2WSGIMiddleware  # noqa
    from a2wsgi.wsgi import WSGIResponder
    from a2wsgi.wsgi_typing import WSGIApp
    from a2wsgi.asgi_typing import HTTPScope, Receive, Send
except ModuleNotFoundError:
    raise RuntimeError(
        "You need to install the package `a2wsgi` to be able to use this middleware. "
        "Simply run `pip install a2wsgi`."
    ) from None


class BufferedWSGIResponder(WSGIResponder):
    """
    Extends `a2wsgi.wsgi.WSGIResponder` to buffer all ASGI messages.

    This responder ensures that responses from the WSGI application are not
    immediately sent to the client. Instead, they are buffered. This allows
    the middleware to inspect the full response (including status code and
    body) before flushing it. If the WSGI application raises an error or
    returns an error status, the buffered response can be discarded, and the
    error can be handled by the ASGI application's exception handlers.
    """

    def __init__(
        self,
        wsgi_app: WSGIApp,
        executor: ThreadPoolExecutor,
        send_queue_size: int,
        scope: HTTPScope,
        receive: Receive,
        send: Send,
        app: Lilya,
        exception_class: type[HTTPException],
    ):
        """
        Initializes the BufferedWSGIResponder.

        Args:
            wsgi_app: The WSGI application to be executed.
            executor: The `ThreadPoolExecutor` used to run the WSGI application
                in a separate thread.
            send_queue_size: The maximum size of the internal queue used to buffer
                messages being sent from the WSGI application.
            scope: The ASGI scope dictionary for the current request.
            receive: The ASGI receive callable for the current request.
            send: The ASGI send callable for the current request.
            app: The main Lilya application instance, used for accessing
                exception handlers.
            exception_class: The type of `HTTPException` to use if an error
                needs to be redirected and handled by Lilya's exception handlers.
        """
        # Call the base class constructor.
        super().__init__(wsgi_app, executor, send_queue_size)
        self._buffer: list[Any] = []  # Initialize an empty list to store buffered messages.
        self._scope = scope
        self._receive = receive
        self._send = send
        self._asgi_app = app  # Store the Lilya application instance.
        self._exception_class = exception_class

    def send(self, message: Any) -> None:
        """
        Buffers an ASGI message instead of sending it directly.

        This method overrides the base `WSGIResponder.send` to capture all
        outgoing ASGI messages from the WSGI application into an internal buffer.

        Args:
            message: The ASGI message to be buffered (e.g., {'type': 'http.response.start'}).
        """
        self._buffer.append(message)

    async def __call__(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """
        Executes the WSGI application and handles the buffered response or errors.

        After the WSGI application completes (or errors), this method inspects
        the buffered response. If an HTTP error status (4xx or 5xx) is detected,
        it attempts to handle the exception using Lilya's exception handlers.
        Otherwise, it flushes all buffered messages to the client.

        Args:
            scope: The ASGI scope dictionary for the current request.
            receive: The ASGI receive callable for the current request.
            send: The ASGI send callable for the current request.
        """
        # Run the base WSGIResponder's __call__ method, which executes the WSGI app.
        # Messages from the WSGI app will be buffered by this class's `send` method.
        await super().__call__(scope, receive, send)

        # Find the 'http.response.start' message in the buffer to get the status code.
        start = next(
            (msg for msg in self._buffer if msg["type"] == "http.response.start"),
            None,
        )
        # Concatenate all 'http.response.body' messages to reconstruct the full body.
        body_bytes = b"".join(m["body"] for m in self._buffer if m["type"] == "http.response.body")

        # Check if an error status code (4xx or 5xx) was returned by the WSGI app.
        if start and start["status"] >= 400:
            # Decode the error body to create a detail message for the exception.
            detail = body_bytes.decode("utf-8", errors="ignore")
            # Create an instance of the configured exception_class.
            exc = self._exception_class(status_code=start["status"], detail=detail)
            # Look up a custom exception handler for this exception class in the Lilya app.

            handler = self._asgi_app.exception_handlers.get(type(exc))

            if handler:
                # If a handler is found, create a Request object.
                # as it might expect specific scope types.
                request = Request(scope, receive=receive)  # type: ignore
                # Await the custom exception handler to get a response.
                response = await handler(request, exc)
                # Send the response generated by the exception handler to the client.
                await response(scope, receive, send)
                return  # Exit, as the error has been handled.

        # If no error or no specific handler was found, flush all buffered messages
        # to the client as a normal response.
        for msg in self._buffer:
            await send(msg)


class WSGIMiddleware(A2WSGIMiddleware):
    """
    A WSGI middleware designed to integrate WSGI applications into an ASGI
    framework, specifically for `Lilya` applications.

    This middleware extends `aiohttp.wsgi.WSGIMiddleware` and adds enhanced
    exception handling capabilities, allowing for the redirection of exceptions
    to a custom HTTP exception class if desired. It manages worker processes
    and message queues for efficient communication between the ASGI and WSGI
    environments.
    """

    def __init__(
        self,
        app: WSGIApp | str,
        workers: int = 10,
        send_queue_size: int = 10,
        redirect_exceptions: bool = False,
        exception_class: type[HTTPException] = HTTPException,
    ) -> None:
        """
        Initializes the WSGIMiddleware.

        Args:
            app: The WSGI application instance or a string import path to it.
                If a string, the application will be dynamically imported.
            workers: The number of worker processes to use for handling WSGI requests.
                This controls the concurrency of WSGI application processing.
            send_queue_size: The maximum size of the queue used for sending
                responses back from the WSGI workers to the ASGI server.
            redirect_exceptions: A boolean flag indicating whether exceptions
                raised by the WSGI application should be caught and transformed
                into the specified `exception_class`. If False, exceptions
                are propagated as-is.
            exception_class: The HTTP exception class to use when `redirect_exceptions`
                is True. Exceptions from the WSGI app will be converted into
                instances of this class. Defaults to `litestar.exceptions.HTTPException`.
        """
        if isinstance(app, str):
            app = cast(WSGIApp, import_string(app))
        super().__init__(app, workers, send_queue_size)
        self.redirect_exceptions = redirect_exceptions
        self._exception_class = exception_class

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The ASGI callable method for the middleware.

        This method processes the incoming ASGI scope, receive, and send functions.
        It either delegates directly to the parent WSGI middleware's `__call__`
        method or wraps the WSGI application with a `BufferedWSGIResponder`
        to handle exception redirection.

        Args:
            scope: The ASGI scope dictionary, containing connection information.
            receive: The ASGI receive callable, used to get incoming messages.
            send: The ASGI send callable, used to send outgoing messages.
        """
        app: Lilya = scope["app"]

        if not self.redirect_exceptions:
            # If exception redirection is not enabled,
            # simply delegate to the parent class's __call__ method.
            # overrides or base class call signatures, which can happen with complex
            # inheritance from external libraries.
            await super().__call__(scope, receive, send)  # type: ignore
        else:
            # If exception redirection is enabled, create a BufferedWSGIResponder.
            # This responder will catch exceptions from the WSGI app and wrap them
            # in the configured _exception_class.
            responder = BufferedWSGIResponder(
                self.app,  # The WSGI application instance.
                self.executor,  # The thread pool executor for WSGI processing.
                self.send_queue_size,  # The size of the send queue.
                cast(HTTPScope, scope),  # Cast scope to HTTPScope for responder's requirements.
                receive,  # The ASGI receive callable.
                send,  # The ASGI send callable.
                app=app,  # Pass the ASGI application instance.
                exception_class=self._exception_class,  # The custom exception class for redirection.
            )
            return await responder(cast(HTTPScope, scope), receive, send)
