from __future__ import annotations

from warnings import warn

from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send

warn("This module is deprecated without replacement", DeprecationWarning, stacklevel=2)


class ApplicationSettingsMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Middleware method that is called for each request.

        Args:
            scope (Scope): The ASGI scope for the request.
            receive (Receive): The ASGI receive function.
            send (Send): The ASGI send function.
        """
        await self.app(scope, receive, send)
