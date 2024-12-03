from __future__ import annotations

from abc import ABC

from lilya.context import g
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class GlobalContextMiddleware(ABC, MiddlewareProtocol):
    """
    GlobalContextMiddleware is an ASGI middleware that initializes a global context for each request.

    This middleware inherits from ABC and MiddlewareProtocol, ensuring it adheres to the ASGI middleware interface.

    Attributes:
        app (ASGIApp): The ASGI application instance.

    Methods:
        __init__(app: ASGIApp):
            Initializes the middleware with the given ASGI application.

        __call__(scope: Scope, receive: Receive, send: Send) -> None:
            Asynchronously handles the incoming request, sets up a new global context,
            and then calls the next middleware or application in the stack.

    Usage:
        This middleware should be added to the ASGI application stack to ensure that
        a fresh global context is available for each request. This can be useful for
        storing request-specific data that needs to be accessed globally within the
        request lifecycle.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Asynchronous call method to set up the global context and then call the parent class's __call__ method.

        Args:
            scope (Scope): The scope of the ASGI application.
            receive (Receive): The receive function to get messages from the client.
            send (Send): The send function to send messages to the client.

        Returns:
            None
        """
        try:
            await self.app(scope, receive, send)
        finally:
            g.clear()
            print(id(g))
