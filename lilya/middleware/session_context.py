from __future__ import annotations

from lilya.context import SessionContext
from lilya.enums import ScopeType
from lilya.exceptions import ImproperlyConfigured
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class SessionContextMiddleware(MiddlewareProtocol):
    """
    Middleware to manage session context in an ASGI application.
    """

    def __init__(self, app: ASGIApp, sub_path: str = "") -> None:
        """
        Initializes the SessionContextMiddleware with the given ASGI application.
        """
        self.app = app
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}
        self.sub_path = sub_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, sets the session context, and resets after request processing.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        try:
            session = scope["session"]
            if not isinstance(session, dict):
                raise KeyError
        except KeyError:
            raise ImproperlyConfigured(
                "'session' not set. Ensure 'SessionMiddleware' is properly installed."
            ) from None

        if self.sub_path:
            session = session.setdefault(self.sub_path, {})

        # Set the session context
        token = SessionContext.set_session(session)
        try:
            await self.app(scope, receive, send)
        finally:
            SessionContext.reset_context(token)
