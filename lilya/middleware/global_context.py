from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Any

from lilya._internal._connection import Connection
from lilya.context import G, g_context
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class GlobalContextMiddleware(ABC, MiddlewareProtocol):
    """
    GlobalContextMiddleware is an ASGI middleware that initializes a global context for each request.

    This middleware inherits from ABC and MiddlewareProtocol, ensuring it adheres to the ASGI middleware interface.

    Args:
        app (ASGIApp): The ASGI application to wrap.
        populate_context: (Callable[[Connection], dict[str, Any] | Awaitable[dict[str, Any]]]):
            An optional function for providing initial data to global contexts.
            Can be used to copy data from a parent global context.

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

    def __init__(
        self,
        app: ASGIApp,
        populate_context: Callable[[Connection], dict[str, Any] | Awaitable[dict[str, Any]]]
        | None = None,
    ) -> None:
        super().__init__(app)
        self.app = app
        self.populate_context = populate_context
        self.scopes: set[str] = {ScopeType.HTTP, ScopeType.WEBSOCKET}

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
        # e.g. lifespans
        if scope["type"] not in self.scopes:
            await self.app(scope, receive, send)
            return
        initial_context: Any = None
        if self.populate_context is not None:
            initial_context = self.populate_context(Connection(scope))
            if isawaitable(initial_context):
                initial_context = await initial_context
        token = g_context.set(G(initial_context))
        try:
            await self.app(scope, receive, send)
        finally:
            g_context.reset(token)


class LifespanGlobalContextMiddleware(GlobalContextMiddleware):
    """
    LifespanGlobalContextMiddleware is an ASGI middleware that initializes a global context for each lifespan request (start/stop).
    """

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super().__init__(app)
        self.scopes = {ScopeType.LIFESPAN}
