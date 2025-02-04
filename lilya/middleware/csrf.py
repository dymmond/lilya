from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Literal

from lilya.datastructures import Cookie, Header
from lilya.enums import ScopeType
from lilya.exceptions import PermissionDenied
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.types import ASGIApp, Message, Receive, Scope, Send

CSRF_SECRET_BYTES = 32
CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


class CSRFMiddleware(MiddlewareProtocol):
    """
    CSRF Middleware class.

    This Middleware protects against attacks by setting a CSRF cookie with a token
    and verifying it in request headers.

    Args:
        app: The 'next' ASGI app to call.
        config: The CSRFConfig instance.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret: str,
        cookie_name: str | None = None,
        header_name: str | None = None,
        cookie_path: str | None = None,
        safe_methods: set[str] | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
        domain: str | None = None,
    ) -> None:
        super().__init__(app)
        self.app = app
        self.secret = secret
        self.cookie_name = cookie_name or "csrftoken"
        self.header_name = header_name or "X-CSRFToken"
        self.cookie_path = cookie_path or "/"
        self.safe_methods = safe_methods or {"GET", "HEAD"}
        self.cookie_secure = secure
        self.cookie_httponly = httponly
        self.cookie_samesite = samesite
        self.cookie_domain = domain

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, checks for CSRF token, and processes the request accordingly.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive, send=send)
        csrf_cookie = request.cookies.get(self.cookie_name)
        current_token = request.headers.get(self.header_name)

        if request.method in self.safe_methods:
            await self.app(scope, receive, self.get_send_wrapper(send, csrf_cookie))
        elif self._csrf_tokens_match(current_token, csrf_cookie):
            await self.app(scope, receive, send)
        else:
            raise PermissionDenied(detail="CSRF token verification failed.")

    def get_send_wrapper(self, send: Send, csrf_cookie: str | None) -> Send:
        """
        Wraps the original send function to inject a CSRF cookie if needed.

        Args:
            send: The original ASGI send function.
            csrf_cookie: The CSRF token from the request.

        Returns:
            Wrapped send function.
        """

        async def send_wrapper(message: Message) -> None:
            """
            Send function that wraps the original send to inject a cookie.

            Args:
                message: An ASGI 'Message'

            Returns:
                None
            """
            if csrf_cookie is None and message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message = self._set_cookie_if_needed(message)
            await send(message)

        return send_wrapper

    def _set_cookie_if_needed(self, message: Message) -> Message:
        """
        Sets CSRF cookie in the response headers if not present.

        Args:
            message: An ASGI 'Message'
        """
        # we need to update the message
        headers = Header.ensure_header_instance(scope=message)
        if "set-cookie" not in headers:
            cookie = Cookie(
                key=self.cookie_name,
                value=self._generate_csrf_token(),
                path=self.cookie_path,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=self.cookie_samesite,
                domain=self.cookie_domain,
            )
            headers.add("set-cookie", cookie.to_header(header=""))
        return message

    def _generate_csrf_hash(self, token: str) -> str:
        """
        Generate an HMAC that signs the CSRF token.

        Args:
            token: The CSRF token.

        Returns:
            Signed HMAC of the token.
        """
        return hmac.new(self.secret.encode(), token.encode(), hashlib.sha256).hexdigest()

    def _generate_csrf_token(self) -> str:
        """
        Generate a CSRF token that includes a randomly generated string signed by an HMAC.

        Returns:
            CSRF token.
        """
        token = secrets.token_hex(CSRF_SECRET_BYTES)
        token_hash = self._generate_csrf_hash(token)
        return token + token_hash

    def _decode_csrf_token(self, token: str) -> str | None:
        """
        Decode a CSRF token and validate its HMAC.

        Args:
            token: The CSRF token.

        Returns:
            Decoded CSRF token if valid, otherwise None.
        """
        if len(token) < CSRF_SECRET_LENGTH + 1:
            return None

        token_secret = token[:CSRF_SECRET_LENGTH]
        existing_hash = token[CSRF_SECRET_LENGTH:]
        expected_hash = self._generate_csrf_hash(token_secret)
        if not secrets.compare_digest(existing_hash, expected_hash):
            return None

        return token_secret

    def _csrf_tokens_match(
        self, request_csrf_token: str | None, cookie_csrf_token: str | None
    ) -> bool:
        """
        Takes the CSRF tokens from the request and the cookie and verifies both are valid and identical.

        Args:
            request_csrf_token: CSRF token from the request headers.
            cookie_csrf_token: CSRF token from the cookie.

        Returns:
            True if tokens are valid and identical, False otherwise.
        """
        if not (request_csrf_token and cookie_csrf_token):
            return False

        decoded_request_token = self._decode_csrf_token(request_csrf_token)
        decoded_cookie_token = self._decode_csrf_token(cookie_csrf_token)
        if decoded_request_token is None or decoded_cookie_token is None:
            return False

        return secrets.compare_digest(decoded_request_token, decoded_cookie_token)
