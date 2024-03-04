from __future__ import annotations

from lilya.datastructures import URL
from lilya.enums import ScopeType
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.responses import RedirectResponse
from lilya.types import ASGIApp, Receive, Scope, Send


class HTTPSRedirectMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Process the incoming request and perform HTTPS redirection if necessary.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        if self._should_redirect(scope):
            redirect_url = self._build_redirect_url(scope)
            response = RedirectResponse(redirect_url, status_code=307)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    def _should_redirect(self, scope: Scope) -> bool:
        """
        Check if redirection to HTTPS is required.

        Args:
            scope (Scope): The ASGI scope.

        Returns:
            bool: True if redirection is required, False otherwise.
        """
        return scope["type"] in (ScopeType.HTTP, ScopeType.WEBSOCKET) and scope["scheme"] in (
            "http",
            "ws",
        )

    def _build_redirect_url(self, scope: Scope) -> URL:
        """
        Build the URL for redirection.

        Args:
            scope (Scope): The ASGI scope.

        Returns:
            URL: The redirection URL.
        """
        url = URL.build_from_scope(scope=scope)
        redirect_scheme = {"http": "https", "ws": "wss"}[url.scheme]
        netloc = url.hostname if url.port in (80, 443) else url.netloc
        return url.replace(scheme=redirect_scheme, netloc=netloc)
