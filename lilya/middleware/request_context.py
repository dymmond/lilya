from __future__ import annotations

from abc import ABC

from lilya.context import RequestContext
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.types import ASGIApp, Receive, Scope, Send


class RequestContextMiddleware(ABC, MiddlewareProtocol):
    """
    Middleware to manage request context in an ASGI application.

    This middleware ensures that the request context is properly set and reset
    for each incoming HTTP request. It uses a global request context to store
    the current request, which can be accessed throughout the application.

    Attributes:
        app (ASGIApp): The ASGI application instance.

    Methods:
        __init__(app: ASGIApp):
            Initializes the middleware with the given ASGI application.

        __call__(scope: Scope, receive: Receive, send: Send) -> None:
            Handles incoming requests, sets the request context, and ensures
            it is reset after the request is processed.
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Initializes the RequestContextMiddleware with the given ASGI application.

        Args:
            app (ASGIApp): The ASGI application instance.
        """
        super().__init__(app)
        self.app = app
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, sets the request context, and ensures it is reset after the request is processed.

        Args:
            scope (Scope): The scope of the request, containing information such as type, path, headers, etc.
            receive (Receive): The receive function to get messages from the client.
            send (Send): The send function to send messages to the client.

        If the request type is "http", it sets the global request context with the current request.
        After processing the request, it resets the request context to ensure no residual data is left.
        """
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return

        global_request = Request(scope, receive, send)
        token = RequestContext.set_request(global_request)
        try:
            await self.app(scope, global_request.receive, global_request.send)
        finally:
            RequestContext.reset_request(token)
