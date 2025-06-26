from __future__ import annotations

import typing

from lilya.datastructures import URL, Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.responses import PlainText
from lilya.types import ASGIApp, Receive, Scope, Send

ENFORCE_DOMAIN_WILDCARD = "Domain wildcard patterns must be as per example '*.example.com'."


class TrustedReferrerMiddleware(MiddlewareProtocol):
    scope_flag_name: str = "referrer_is_trusted"

    def __init__(
        self,
        app: ASGIApp,
        allowed_referrers: typing.Iterable[str] | None = None,
        allow_same_origin: bool = True,
        block_untrusted_referrers: bool = False,
    ) -> None:
        """
        Middleware for enforcing trusted host headers in incoming requests.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            allowed_referrers (Optional[Iterable[str]]): List of allowed host patterns of referrers. Defaults to empty set..
            allow_same_origin (bool): Whether to include the same origin. Defaults to True.
            block_untrusted_referrers (bool): Whether to block untrusted referrers. Defaults to False.
        """
        if allowed_referrers is None:
            allowed_referrers = set()
        else:
            allowed_referrers = set(allowed_referrers)

        for pattern in allowed_referrers:
            assert "*" not in pattern[1:], ENFORCE_DOMAIN_WILDCARD
            if pattern.startswith("*") and pattern != "*":
                assert pattern.startswith("*."), ENFORCE_DOMAIN_WILDCARD

        self.app = app
        self.allowed_referrers = allowed_referrers
        self.allow_any = "*" in self.allowed_referrers
        self.allow_empty = "" in self.allowed_referrers
        self.allow_same_origin = allow_same_origin
        self.block_untrusted_referrers = block_untrusted_referrers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI application callable.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Header.ensure_header_instance(scope=scope)
        host = headers.get("host", "").split(":")[0]
        # http has a misspelled referrer header, see specs
        referrer = headers.get("referer", "")
        scope[self.scope_flag_name] = referrer_is_trusted = self.validate_referrer(referrer, host)
        response = self.app
        if self.block_untrusted_referrers and not referrer_is_trusted:
            response = PlainText("Invalid referrer", status_code=400)
        await response(scope, receive, send)

    def validate_referrer(self, referrer: str, host: str) -> bool:
        """
        Validate the host header against the allowed host patterns.

        Args:
            referrer (str): Referer header value.
            host (str): Host header value.

        Returns:
            bool: Is a trusted referrer.
        """
        if self.allow_any:
            return True
        if not referrer:
            return self.allow_empty
        referrer_host = URL(referrer).hostname.split(":")[0]
        if self.allow_same_origin and referrer_host == host:
            return True

        is_valid_host = False
        for pattern in self.allowed_referrers:
            if referrer_host == pattern or (
                pattern.startswith("*") and referrer_host.endswith(pattern[1:])
            ):
                is_valid_host = True
                break
        return is_valid_host
