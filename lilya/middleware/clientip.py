from __future__ import annotations

from collections.abc import Sequence

from lilya.clientip import get_ip
from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class ClientIPMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: None | Sequence[str] = None,
    ) -> None:
        """
        Middleware for setting the real ip.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            trusted_proxies (Optional[Sequence[str]]): List of trusted proxy ips.
                                                       Leave None to use the lily settings.
                                                       Set to ["*"] for trusting all proxies.
                                                       Use "unix" for unix sockets.
        """
        self.app = app
        self.trusted_proxies = trusted_proxies

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        headers: Header = Header.from_scope(scope)
        scope["real-clientip"] = headers["x-real-ip"] = get_ip(
            scope, trusted_proxies=self.trusted_proxies
        )
        scope["headers"] = headers.get_multi_items()

        await self.app(scope, receive, send)
