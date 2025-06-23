from __future__ import annotations

from collections.abc import Sequence

from lilya.clientip import get_ip
from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class ClientIPScopeOnlyMiddleware(MiddlewareProtocol):
    scope_name: str = "real-clientip"

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

    def update_scope(self, scope: Scope) -> None:
        scope[self.scope_name] = get_ip(scope, trusted_proxies=self.trusted_proxies)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        self.update_scope(scope)
        await self.app(scope, receive, send)


class ClientIPMiddleware(ClientIPScopeOnlyMiddleware):
    def update_scope(self, scope: Scope) -> None:
        super().update_scope(scope)
        headers: Header = Header.ensure_header_instance(scope)
        headers["x-real-ip"] = scope[self.scope_name]
