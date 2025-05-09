from __future__ import annotations

from lilya._internal._connection import Connection
from lilya.context import SessionContext
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
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
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, sets the session context, and resets after request processing.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        connection = Connection(scope)

        # Initialize session if not already initialized
        if not hasattr(connection, "session"):
            connection.session = {}

        # Set the session context
        token = SessionContext.set_connection(connection)
        try:
            await self.app(scope, receive, send)
        finally:
            SessionContext.reset_context(token)
