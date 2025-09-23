from __future__ import annotations

import re
import urllib.parse
from typing import Literal

from lilya.conf import _monkay
from lilya.contrib.security.csrf import generate_csrf_token, tokens_match
from lilya.datastructures import Cookie, Header
from lilya.enums import MediaType, ScopeType
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
        form_field_name: str | None = None,
        max_body_size: int = 2 * 1024 * 1024,
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
        self.form_field_name = form_field_name or _monkay.settings.csrf_token_name
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, checks for CSRF token, and processes the request accordingly.
        """
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive, send=send)
        csrf_cookie = request.cookies.get(self.cookie_name)

        # 1) Primary source: header
        current_token = request.headers.get(self.header_name)

        # 2) Fallback for unsafe methods: form field from body
        recv_for_app = receive  # default: pass-through to downstream
        if (not current_token) and (request.method not in self.safe_methods):
            content_type = request.headers.get("content-type", "")
            if self._is_form_content_type(content_type):
                body_bytes, replay_receive = await self._read_and_replay_body(receive)
                if body_bytes is not None:
                    current_token = self._extract_token_from_body(
                        body_bytes, content_type, self.form_field_name
                    )
                    recv_for_app = replay_receive  # ensure downstream still sees the original body

        if request.method in self.safe_methods:
            await self.app(scope, receive, self.get_send_wrapper(send, csrf_cookie))
            return

        if tokens_match(self.secret, current_token, csrf_cookie):
            await self.app(scope, recv_for_app, send)
            return

        raise PermissionDenied(detail="CSRF token verification failed.")

    def _is_form_content_type(self, content_type: str) -> bool:
        """
        Check if the content type is form-related.

        Args:
            content_type: The content type string.
        """
        ctype = (content_type or "").lower()
        return MediaType.MULTIPART in ctype or MediaType.URLENCODED in ctype

    async def _read_and_replay_body(self, receive: Receive) -> tuple[bytes | None, Receive]:
        """
        Read the entire request body from the ASGI receive channel and create a
        new receive function that replays the same body to the downstream app.

        Returns (body_bytes or None if too large, replay_receive).
        """
        chunks: list[bytes] = []
        total = 0
        more_body = True

        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                # Ignore other events for CSRF purposes
                continue
            chunk = message.get("body", b"") or b""
            if chunk:
                total += len(chunk)
                if total > self.max_body_size:
                    # Too large to buffer safely; construct a minimal replay
                    buffered = b"".join(chunks)

                    async def replay_receive_internal() -> Message:
                        nonlocal buffered
                        data, buffered = buffered, b""
                        return {"type": "http.request", "body": data, "more_body": False}

                    return None, replay_receive_internal
                chunks.append(chunk)
            more_body = message.get("more_body", False)

        body = b"".join(chunks)

        sent = False

        async def replay_receive() -> Message:
            nonlocal sent, body
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            # Subsequent calls: empty message
            return {"type": "http.request", "body": b"", "more_body": False}

        return body, replay_receive

    def _extract_token_from_body(self, body: bytes, content_type: str, field: str) -> str | None:
        """
        Extracts a token from the request body based on the specified content type and field name.
        Supports extraction from bodies with content types:

        - application/x-www-form-urlencoded: Parses URL-encoded form data and retrieves the value for the given field.

        - multipart/form-data: Parses multipart form data and retrieves the value for the given field using boundary-based extraction.

        Args:
            body (bytes): The raw request body.
            content_type (str): The Content-Type header value of the request.
            field (str): The name of the field to extract from the body.
        Returns:
            str | None: The extracted token value if found, otherwise None.

        """
        ctype = (content_type or "").lower()

        if MediaType.URLENCODED in ctype:
            try:
                text = body.decode("utf-8", errors="ignore")
            except Exception:
                return None
            parsed = urllib.parse.parse_qs(text, keep_blank_values=True, strict_parsing=False)
            values = parsed.get(field)
            return values[0] if values else None

        if MediaType.MULTIPART in ctype:
            # Minimal boundary-based extractor for a simple text field
            match = re.search(r"boundary=([^;]+)", ctype)

            if not match:
                return None  # type: ignore

            boundary = match.group(1).strip().strip('"')
            if not boundary:
                return None

            delimiter = ("--" + boundary).encode("ascii", "ignore")
            end_delimiter = ("--" + boundary + "--").encode("ascii", "ignore")
            parts = body.split(delimiter)

            for part in parts:
                if not part or part.startswith(b"--") or part == end_delimiter:
                    continue

                header_sep = part.find(b"\r\n\r\n")
                if header_sep < 0:
                    header_sep = part.find(b"\n\n")
                    if header_sep < 0:
                        continue

                raw_headers = part[:header_sep].decode("utf-8", errors="ignore")
                content = part[header_sep + 4 :].strip(b"\r\n")

                # Look for name="field"
                if re.search(rf'name="(?:{re.escape(field)})"(;|$)', raw_headers):
                    try:
                        return content.decode("utf-8", errors="ignore")
                    except Exception:
                        return None
        return None

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
                value=generate_csrf_token(self.secret),
                path=self.cookie_path,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=self.cookie_samesite,
                domain=self.cookie_domain,
            )
            headers.add("set-cookie", cookie.to_header(header=""))
        return message
