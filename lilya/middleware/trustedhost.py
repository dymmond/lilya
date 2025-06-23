from __future__ import annotations

import typing

from lilya.datastructures import URL, Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.responses import PlainText, RedirectResponse, Response
from lilya.types import ASGIApp, Receive, Scope, Send

ENFORCE_DOMAIN_WILDCARD = "Domain wildcard patterns must be as per example '*.example.com'."


class TrustedHostMiddleware(MiddlewareProtocol):
    scope_flag_name: str = "host_is_trusted"

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: typing.Iterable[str] | None = None,
        www_redirect: bool = True,
        block_untrusted_hosts: bool = True,
    ) -> None:
        """
        Middleware for enforcing trusted host headers in incoming requests.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            allowed_hosts (Optional[Iterable[str]]): List of allowed host patterns. Defaults to ["*"].
            www_redirect (bool): Whether to redirect requests with missing 'www.' to 'www.' prefixed URLs. Defaults to True.
            block_untrusted_hosts (bool): Whether to block the request or just add  = True,
        """
        if allowed_hosts is None:
            allowed_hosts = {"*"}
        else:
            allowed_hosts = set(allowed_hosts)

        for pattern in allowed_hosts:
            assert "*" not in pattern[1:], ENFORCE_DOMAIN_WILDCARD
            if pattern.startswith("*") and pattern != "*":
                assert pattern.startswith("*."), ENFORCE_DOMAIN_WILDCARD

        self.app = app
        self.allowed_hosts = allowed_hosts
        self.allow_any = "*" in self.allowed_hosts
        self.www_redirect = www_redirect
        self.block_untrusted_hosts = block_untrusted_hosts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        if self.allow_any or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Header.ensure_header_instance(scope=scope)
        host = headers.get("host", "").split(":")[0]
        is_valid_host, found_www_redirect = self.validate_host(host)

        if is_valid_host:
            scope[self.scope_flag_name] = True
            await self.app(scope, receive, send)
        else:
            await self.handle_invalid_host(scope, receive, send, found_www_redirect)

    def validate_host(self, host: str) -> tuple[bool, bool]:
        """
        Validate the host header against the allowed host patterns.

        Args:
            host (str): Host header value.

        Returns:
            Tuple[bool, bool]: (is_valid_host, found_www_redirect).
        """
        is_valid_host = False
        found_www_redirect = False
        for pattern in self.allowed_hosts:
            if host == pattern or (pattern.startswith("*") and host.endswith(pattern[1:])):
                is_valid_host = True
                break
            elif "www." + host == pattern:
                found_www_redirect = True
        return is_valid_host, found_www_redirect

    async def handle_invalid_host(
        self, scope: Scope, receive: Receive, send: Send, found_www_redirect: bool
    ) -> None:
        """
        Handle requests with invalid host headers.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
            found_www_redirect (bool): Whether 'www.' redirect was found.
        """
        response: Response | ASGIApp
        scope[self.scope_flag_name] = False
        if found_www_redirect and self.www_redirect:
            url = URL.build_from_scope(scope=scope)
            redirect_url = url.replace(netloc="www." + url.netloc)
            response = RedirectResponse(url=str(redirect_url))
        elif self.block_untrusted_hosts:
            response = PlainText("Invalid host header", status_code=400)
        else:
            response = self.app
        await response(scope, receive, send)
