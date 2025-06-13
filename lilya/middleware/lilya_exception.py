import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from lilya import status
from lilya.enums import MediaType
from lilya.exceptions import HTTPException
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.responses import Response
from lilya.types import ASGIApp, Receive, Scope, Send


@dataclass
class Content:
    status_code: int | None = None
    detail: str | None = None
    extra: dict[str, Any] | None = None

    def dict(self, exclude_none: bool = False, upper: bool = False) -> dict[str, Any]:
        """
        Dumps all the settings into a python dictionary.
        """
        original = asdict(self)

        if not exclude_none:
            if not upper:
                return original
            return {k.upper(): v for k, v in original.items()}

        if not upper:
            return {k: v for k, v in original.items() if v is not None}
        return {k.upper(): v for k, v in original.items() if v is not None}


class LilyaExceptionMiddleware(MiddlewareProtocol):
    """
    Middleware for handling exceptions raised by an ASGI application within Lilya.

    This middleware intercepts HTTP requests and attempts to catch any exceptions
    raised by the downstream ASGI application. If an exception is caught and
    a corresponding handler is registered, it will be invoked to generate
    an appropriate `Response`. If no handler is found for a specific exception
    type, the exception will be re-raised.
    """

    def __init__(
        self,
        app: ASGIApp,
        handlers: Mapping[Any, Callable[[Request, Exception], Response]] | None = None,
    ):
        """
        Initializes the LilyaExceptionMiddleware.

        Args:
            app: The downstream ASGI application callable. This is typically the
                next middleware or the main application handler in the ASGI stack.
            handlers: An optional mapping where keys are exception types and values
                are asynchronous callable handlers. Each handler should accept
                a `Request` and an `Exception` instance, and return a `Response`.
                If no handlers are provided, an empty mapping is used.
        """
        super().__init__(app)
        self.app = app
        self.handlers = handlers or {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The ASGI callable method for the middleware.

        This method processes incoming ASGI messages. It only applies exception
        handling logic to `http` scope types. For other scope types (e.g.,
        'websocket', 'lifespan'), it passes the request directly to the
        downstream application. For HTTP requests, it wraps the downstream
        application call in a `try-except` block to catch and handle exceptions.

        Args:
            scope: The ASGI scope dictionary, containing connection information.
            receive: The ASGI receive callable, used to get incoming messages.
            send: The ASGI send callable, used to send outgoing messages.
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            handler = self._lookup_handler(exc)
            if handler:
                response = await handler(request, exc)
            else:
                response = self.create_exception_response(exc)
            await response(scope, receive, send)

    def create_exception_response(self, exc: Exception) -> Response:
        """
        Turn any Exception into a JSON Response containing {status_code, detail, extra}
        """
        if isinstance(exc, HTTPException):
            content = Content(detail=exc.detail, status_code=exc.status_code)
            extra = getattr(exc, "extra", {}) or {}
            if extra:
                content.extra = extra
            status_code = exc.status_code
            headers = exc.headers or {}
        else:
            # generic 500 for all other exceptions
            content = Content(detail=str(exc), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            headers = {}

        body = json.dumps(content.dict(exclude_none=True))
        return Response(
            content=body,
            media_type=MediaType.JSON,
            status_code=status_code,
            headers=headers,
        )

    def _lookup_handler(
        self, exc_type: Exception
    ) -> Callable[[Request, Exception], Response] | None:
        """
        Looks up a registered exception handler for a given exception type.

        This method performs an exact match lookup for the exception type in
        the registered handlers. More complex lookup strategies (e.g., walking
        the MRO to find handlers for base exception classes) could be added
        here if more flexibility is desired.

        Args:
            exc_type: The type of the exception for which to find a handler.

        Returns:
            The callable handler for the exception type if found, otherwise None.
        """
        status_code = (
            exc_type.status_code
            if isinstance(exc_type, HTTPException)
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        if not self.handlers:
            return None

        return self.handlers.get(status_code) or self.handlers.get(exc_type.__class__)
