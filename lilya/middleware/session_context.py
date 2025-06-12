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
            global_session = scope["session"]
            if not isinstance(global_session, dict):
                raise KeyError
        except KeyError:
            raise ImproperlyConfigured(
                "'session' not set. Ensure 'SessionMiddleware' is properly installed."
            ) from None

        if self.sub_path:
            session = global_session.setdefault(self.sub_path, {})
        else:
            session = global_session

        # Set the session context
        token = SessionContext.set_session(session)
        try:
            await self.app(scope, receive, send)
        finally:
            # cleanup session, so the main session can get deleted
            if self.sub_path and not session:
                global_session.pop(self.sub_path, None)
            SessionContext.reset_context(token)
