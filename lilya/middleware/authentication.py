from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from lilya._internal._connection import Connection
from lilya.authentication import (
    AnonymousUser,
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    AuthResult,
)
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.responses import PlainText, Response
from lilya.types import ASGIApp, Receive, Scope, Send


class BaseAuthMiddleware(ABC, MiddlewareProtocol):
    """
    `BaseAuthMiddleware` is the object that you can implement if you
    want to implement any `authentication` middleware with Lilya.

    It is not mandatory to use it and you are free to implement your own.

    If you just want to use Authentication you can skip to `AuthenticationMiddleware` and create an AuthenticationBackend.

    Once you have installed the `AuthenticationMiddleware` and
    either provide

     implemented the
    `authenticate`, the `request.user` will be available in any of your
    endpoints.
    """

    def __init__(
        self,
        app: ASGIApp,
        on_error: Callable[[Connection, AuthenticationError], Response] | None = None,
    ) -> None:
        super().__init__(app)
        self.app = app
        self.on_error: Callable[[Connection, Exception], Response] = (
            on_error if on_error is not None else self.default_on_error  # type: ignore
        )
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Function callable that automatically will call the `authenticate` function
        from any middleware subclassing the `BaseAuthMiddleware` and assign the `AuthUser` user
        to the `request.user`.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        conn = Connection(scope)
        try:
            auth_result = await self.authenticate(conn)
        except AuthenticationError as exc:
            await self._process_exception(scope, receive, send, conn, exc)
            return

        if auth_result is None:
            auth_result = AuthCredentials(), AnonymousUser()

        scope["auth"], scope["user"] = auth_result
        await self.app(scope, receive, send)

    @abstractmethod
    async def authenticate(self, conn: Connection) -> None | AuthResult:
        """Authorize users here."""

    async def _process_exception(
        self, scope: Scope, receive: Receive, send: Send, connection: Connection, exc: Exception
    ) -> None:
        """
        Handles exceptions that occur during the processing of a request or WebSocket connection.

        Args:
            scope (Scope): The ASGI scope dictionary containing request/connection information.
            receive (Receive): The ASGI receive callable to receive messages.
            send (Send): The ASGI send callable to send messages.
            connection (Connection): The connection object representing the client connection.
            exc (Exception): The exception that was raised during processing.

        Returns:
            Response: The response to be sent back to the client.
        """
        response = self.on_error(connection, exc)
        if scope["type"] == ScopeType.WEBSOCKET:
            await send({"type": "websocket.close", "code": 1000})
        else:
            await response(scope, receive, send)

    @staticmethod
    def default_on_error(connection: Connection, exc: Exception) -> Response:
        return PlainText(str(exc), status_code=400)


class AuthenticationMiddleware(BaseAuthMiddleware):
    backend: list[AuthenticationBackend]

    def __init__(
        self,
        app: ASGIApp,
        backend: AuthenticationBackend | Sequence[AuthenticationBackend] | None = None,
        on_error: Callable[[Connection, AuthenticationError], Response] | None = None,
    ) -> None:
        super().__init__(app, on_error=on_error)
        if backend is None:
            self.backend = []
        elif isinstance(backend, AuthenticationBackend):
            self.backend = [backend]
        else:
            self.backend = list(backend)
        assert self.backend or (not getattr(self.authenticate, "requires_backend", False)), (
            "'backend' is required for authenticate method. Overwrite 'authenticate' or provide AuthenticationBackend in backend"
        )

    async def authenticate(self, conn: Connection) -> None | AuthResult:
        """Authorize users here."""

        for backend in self.backend:
            # exceptions are passed through to __call__ and there handled
            auth_result = await backend.authenticate(conn)
            if auth_result is not None:
                return auth_result
        return None

    authenticate.requires_backend = True
