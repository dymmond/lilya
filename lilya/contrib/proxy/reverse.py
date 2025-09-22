from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterable

from lilya.types import Receive, Scope, Send

try:
    import httpx
except ImportError as e:
    raise ImportError("httpx is required for lilya.contrib.proxy") from e


class ReverseProxy:
    """
    An ASGI-compatible reverse proxy middleware for Lilya.

    This class forwards incoming HTTP requests to a configured upstream
    target and streams the response back. It handles hop-by-hop header
    filtering, optional cookie domain rewriting, and `X-Forwarded-*`
    header injection.
    """

    def __init__(
        self,
        target_base_url: str,
        *,
        upstream_prefix: str = "/",
        preserve_host: bool = False,
        rewrite_set_cookie_domain: Callable[[str], str] | None = None,
        timeout: httpx.Timeout | float = httpx.Timeout(10, connect=5, read=10, write=10),
        limits: httpx.Limits = httpx.Limits(max_connections=100, max_keepalive_connections=20),
        follow_redirects: bool = False,
        extra_request_headers: dict[str, str] | None = None,
        drop_request_headers: Iterable[str] | None = None,
        drop_response_headers: Iterable[str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """
        Args:
            target_base_url: Base URL of the upstream server.
            upstream_prefix: Path prefix prepended to forwarded requests.
            preserve_host: If True, keeps original Host header.
            rewrite_set_cookie_domain: Optional function to rewrite cookie domains.
            timeout: Timeout for upstream requests.
            limits: Connection pool limits for httpx client.
            follow_redirects: Whether to follow upstream redirects.
            extra_request_headers: Extra headers to add to each request.
            drop_request_headers: Headers to strip from requests.
            drop_response_headers: Headers to strip from responses.
            transport: Optional custom transport for httpx client.
        """
        self._base_url = httpx.URL(target_base_url.rstrip("/"))
        self._upstream_prefix = upstream_prefix
        self._preserve_host = preserve_host
        self._rewrite_cookie_domain = rewrite_set_cookie_domain
        self._timeout = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        self._limits = limits
        self._follow_redirects = follow_redirects
        self._extra_request_headers = extra_request_headers or {}
        self._drop_request_headers = {h.lower() for h in (drop_request_headers or ())}
        self._drop_response_headers = {h.lower() for h in (drop_response_headers or ())}
        self._client: httpx.AsyncClient | None = None
        self._transport = transport

        # Headers that must never be forwarded
        self._hop_by_hop_headers = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailer",
            "transfer-encoding",
            "upgrade",
        }

    async def startup(self) -> None:
        """Initialize the underlying httpx.AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
                follow_redirects=self._follow_redirects,
                transport=self._transport,  # type: ignore
            )

    async def shutdown(self) -> None:
        """Close the httpx client gracefully."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entrypoint to handle incoming requests."""
        if scope["type"] != "http":
            await self._send_text(send, 404, "Not Found")
            return

        assert self._client is not None, "ReverseProxy not started. Call startup() first."

        method = scope["method"]
        upstream_url = self._build_upstream_url(scope)
        request_headers = self._prepare_request_headers(scope)
        request_body = (
            self._build_request_body_stream(receive)
            if method not in ("GET", "HEAD", "OPTIONS")
            else None
        )

        try:
            await self._forward_to_upstream(
                method, upstream_url, request_headers, request_body, send
            )
        except httpx.RequestError as exc:
            await self._send_text(send, 502, f"Upstream error: {exc}")

    # -----------------------------
    # Request / Response helpers
    # -----------------------------

    def _join_paths(self, prefix: str, path: str) -> str:
        """
        Join a prefix and request path into a normalized upstream path.

        Ensures there is exactly one slash between the prefix and the path.

        Args:
            prefix: The upstream prefix configured for the proxy.
            path: The request path from the ASGI scope.

        Returns:
            A joined path string suitable for forwarding upstream.
        """
        if not prefix.endswith("/"):
            prefix += "/"
        return prefix + path.lstrip("/")

    def _build_upstream_url(self, scope: Scope) -> httpx.URL:
        """Construct the target upstream URL based on scope and prefix."""
        raw_path: bytes = scope.get("raw_path", scope["path"].encode("latin-1"))
        query_string: bytes = scope.get("query_string", b"")
        path = raw_path.decode("latin-1")
        upstream_path = self._join_paths(self._upstream_prefix, path)
        return self._base_url.join(upstream_path).copy_with(query=query_string)

    def _prepare_request_headers(self, scope: Scope) -> dict[str, str]:
        """Extract and normalize headers for the upstream request."""
        request_headers: dict[str, str] = {}
        for raw_key, raw_value in scope.get("headers", []):
            key = raw_key.decode("latin-1")
            value = raw_value.decode("latin-1")
            if (
                key.lower() in self._hop_by_hop_headers
                or key.lower() in self._drop_request_headers
            ):
                continue
            request_headers[key] = value

        request_headers.update(self._extra_request_headers)

        if not self._preserve_host:
            request_headers["host"] = self._base_url.host or request_headers.get("host", "")

        # Add forwarding headers
        client_addr = scope.get("client")
        client_ip = client_addr[0] if client_addr else ""
        existing_forwarded_for = request_headers.get("x-forwarded-for")
        request_headers["x-forwarded-for"] = (
            f"{existing_forwarded_for}, {client_ip}"
            if existing_forwarded_for and client_ip
            else client_ip or existing_forwarded_for or ""
        )
        request_headers["x-forwarded-proto"] = (
            "https" if scope.get("scheme") == "https" else "http"
        )
        request_headers["x-forwarded-host"] = request_headers.get("host", "")

        return request_headers

    def _build_request_body_stream(self, receive: Receive) -> AsyncIterator[bytes]:
        """Yield request body chunks from ASGI events."""

        async def body_iter() -> AsyncIterator[bytes]:
            while True:
                event = await receive()
                if event["type"] == "http.request":
                    body = event.get("body", b"")
                    if body:
                        yield body
                    if not event.get("more_body", False):
                        break
                elif event["type"] == "http.disconnect":
                    break

        return body_iter()

    async def _forward_to_upstream(
        self,
        method: str,
        url: httpx.URL,
        headers: dict[str, str],
        content: AsyncIterator[bytes] | None,
        send: Send,
    ) -> None:
        """Stream the request to the upstream and relay the response back."""
        assert self._client is not None

        async with self._client.stream(method, url, headers=headers, content=content) as resp:
            response_headers = self._sanitize_response_headers(resp.headers.items())

            if self._rewrite_cookie_domain is not None:
                response_headers = self._rewrite_response_cookies(resp, response_headers)

            await send(
                {
                    "type": "http.response.start",
                    "status": resp.status_code,
                    "headers": [
                        (k.encode("latin-1"), v.encode("latin-1")) for k, v in response_headers
                    ],
                }
            )

            async for chunk in resp.aiter_bytes():
                await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    # -----------------------------
    # Response helpers
    # -----------------------------

    def _sanitize_response_headers(
        self, headers: Iterable[tuple[str, str]]
    ) -> list[tuple[str, str]]:
        """Remove hop-by-hop and dropped headers from upstream response."""
        sanitized: list[tuple[str, str]] = []
        for key, value in headers:
            lower_key = key.lower()
            if lower_key in self._hop_by_hop_headers or lower_key in self._drop_response_headers:
                continue
            if lower_key in ("transfer-encoding",):
                continue
            sanitized.append((key, value))
        return sanitized

    def _rewrite_response_cookies(
        self,
        response: httpx.Response,
        headers: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Rewrite Set-Cookie headers when a domain rewrite function is provided."""
        cookies = response.headers.get_list("set-cookie")
        if not cookies:
            return headers

        filtered = [(k, v) for k, v in headers if k.lower() != "set-cookie"]
        for cookie in cookies:
            filtered.append(("set-cookie", self._rewrite_cookie(cookie)))
        return filtered

    def _rewrite_cookie(self, cookie_value: str) -> str:
        """Apply rewrite_set_cookie_domain callback to a cookie value."""
        if self._rewrite_cookie_domain is None:
            return cookie_value

        decision = self._rewrite_cookie_domain(cookie_value)
        if decision is None:
            return cookie_value

        parts = [p.strip() for p in cookie_value.split(";") if p.strip()]
        rewritten, domain_seen = [], False
        for part in parts:
            if part.lower().startswith("domain="):
                domain_seen = True
                if decision:
                    rewritten.append(f"Domain={decision}")
            else:
                rewritten.append(part)

        if not domain_seen and decision:
            rewritten.append(f"Domain={decision}")

        return "; ".join(rewritten)

    async def _send_text(self, send: Send, status: int, text: str) -> None:
        """Send a plain-text HTTP response."""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": text.encode("utf-8")})
