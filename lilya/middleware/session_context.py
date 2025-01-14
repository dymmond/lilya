from __future__ import annotations

from lilya.context import SessionContext
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.types import ASGIApp, Receive, Scope, Send


class SessionContextMiddleware(MiddlewareProtocol):
    """
    Middleware to manage session context in an ASGI application.
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Initializes the SessionContextMiddleware with the given ASGI application.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, sets the session context, and resets after request processing.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Initialize session if not already initialized
        if not hasattr(request, "session"):
            request.session = {}

        # Set the session context
        token = SessionContext._session_context.set(request)
        try:
            await self.app(scope, receive, send)
        finally:
            SessionContext.reset_context(token)
