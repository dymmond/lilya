from __future__ import annotations

from collections.abc import Callable, Collection

from lilya.clientip import get_ip
from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class ClientIPScopeOnlyMiddleware(MiddlewareProtocol):
    scope_name: str = "real-clientip"

    def __init__(
        self,
        app: ASGIApp,
        *,
        trusted_proxies: None | Collection[str] = None,
        sanitize_clientip: Callable[[str], str] | None = None,
        sanitize_proxyip: Callable[[str], str] | None = None,
    ) -> None:
        """
        Middleware for setting the real ip.

        Args:
            app (ASGIApp): The ASGI application to wrap.
        Kwargs:
            trusted_proxies (Optional[Collection[str]]): List of trusted proxy ips.
                                                       Leave None to use the lily settings.
                                                       Set to ["*"] for trusting all proxies.
                                                       Use "unix" for unix sockets.
            sanitize_proxyip (Optional[Callable[[str], str]]): Sanitize ip before comparing with proxies (ip of proxy).
            sanitize_clientip (Optional[Callable[[str], str]]): Sanitize ip retrieved from proxy for outputting.
                                                                This is probably what you want to provide.
        """
        self.app = app
        self.trusted_proxies = trusted_proxies
        self.sanitize_clientip = sanitize_clientip
        self.sanitize_proxyip = sanitize_proxyip

    def update_scope(self, scope: Scope) -> None:
        scope[self.scope_name] = get_ip(
            scope,
            trusted_proxies=self.trusted_proxies,
            sanitize_clientip=self.sanitize_clientip,
            sanitize_proxyip=self.sanitize_proxyip,
        )

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
