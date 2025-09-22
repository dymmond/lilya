from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterable

from lilya.types import Receive, Scope, Send

try:
    import httpx
except ImportError as e:
    raise ImportError("httpx is required for lilya.contrib.proxy") from e


class ReverseProxy:
    """
    An ASGI-compatible reverse proxy middleware/component for Lilya.

    This class allows you to mount a Lilya application as a reverse proxy
    that forwards incoming requests to a specified upstream target server
    and streams back the response.

    It uses `httpx.AsyncClient` under the hood to handle upstream connections
    with support for streaming, connection pooling, cookie domain rewriting,
    and customizable request/response header filtering.

    Typical use case:
    ```python
    from lilya import Lilya
    from lilya.contrib.proxy import ReverseProxy

    proxy = ReverseProxy("https://example.com", upstream_prefix="/api")

    app = Lilya(routes=[
        Mount("/proxy", app=proxy),
    ])

    @app.on_startup
    async def start_proxy():
        await proxy.startup()

    @app.on_shutdown
    async def stop_proxy():
        await proxy.shutdown()
    ```

    Args:
        target_base_url: Base URL of the upstream server to forward requests to.
        upstream_prefix: Path prefix prepended before forwarding to upstream.
        preserve_host: If True, preserves the incoming `Host` header instead of
            rewriting it to the upstream host.
        rewrite_set_cookie_domain: Optional callable for rewriting `Set-Cookie`
            domains on the upstream response. Receives the raw cookie string and
            must return the replacement domain (or empty string to drop).
        timeout: Timeout settings for upstream requests. Accepts either
            `httpx.Timeout` or a float (seconds).
        limits: Connection limits for the underlying `httpx.AsyncClient`.
        follow_redirects: Whether to follow upstream redirects automatically.
        extra_request_headers: Extra headers to add to every forwarded request.
        drop_request_headers: Request headers to strip before proxying upstream.
        drop_response_headers: Response headers to strip from upstream before
            sending back to the client.
        transport: Optional custom transport for `httpx.AsyncClient`.

    Raises:
        ImportError: If `httpx` is not installed.
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
        if drop_request_headers is None:
            drop_request_headers = ()

        if drop_response_headers is None:
            drop_response_headers = ()

        self._base = httpx.URL(target_base_url.rstrip("/"))
        self._upstream_prefix = upstream_prefix
        self._preserve_host = preserve_host
        self._rewrite_cookie_domain = rewrite_set_cookie_domain
        self._timeout = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        self._limits = limits
        self._follow_redirects = follow_redirects
        self._extra_req_headers = extra_request_headers or {}
        self._drop_req_headers = {h.lower() for h in drop_request_headers}
        self._drop_resp_headers = {h.lower() for h in drop_response_headers}
        self._client: httpx.AsyncClient | None = None
        self._transport = transport

        self._hop_by_hop = {
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
        """
        Initialize the underlying `httpx.AsyncClient`.

        Must be called during application startup before the proxy
        can process requests.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
                follow_redirects=self._follow_redirects,
                transport=self._transport,  # type: ignore
            )

    async def shutdown(self) -> None:
        """
        Gracefully close the upstream client session.

        Should be called during application shutdown to release resources
        and close idle connections.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI entrypoint for handling requests.

        For HTTP requests, forwards the request to the configured upstream
        server and streams the response back to the client.

        For non-HTTP scopes, returns a 404 `Not Found`.

        Args:
            scope: The ASGI connection scope dictionary.
            receive: Awaitable to receive events (e.g. request body).
            send: Awaitable to send events (e.g. response data).
        """
        if scope["type"] != "http":
            await self.not_found(send)
            return

        assert self._client is not None, "ReverseProxy not started. Call startup() on app startup."

        method = scope["method"]
        raw_path: bytes = scope.get("raw_path", scope["path"].encode("latin-1"))
        query_string: bytes = scope.get("query_string", b"")

        # Build upstream path: mount path is already stripped by the router when mounted.
        # Combine upstream_prefix + path
        path = raw_path.decode("latin-1")
        upstream_path = self._join_paths(self._upstream_prefix, path)
        upstream_url = self._base.join(upstream_path).copy_with(query=query_string)

        # Build request headers
        headers = self._extract_request_headers(scope)

        # Request body stream (pass-through)
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

        content = body_iter() if method not in ("GET", "HEAD", "OPTIONS") else None

        try:
            async with self._client.stream(
                method, upstream_url, headers=headers, content=content
            ) as upstream_resp:
                status_code = upstream_resp.status_code
                response_headers = self._filter_response_headers(upstream_resp.headers.items())

                # Optional cookie domain rewrite
                if self._rewrite_cookie_domain is not None:
                    cookies = upstream_resp.headers.get_list("set-cookie")
                    if cookies:
                        # Remove originals
                        response_headers = [
                            (k, v) for (k, v) in response_headers if k.lower() != "set-cookie"
                        ]
                        # Add rewritten
                        for c in cookies:
                            response_headers.append(("set-cookie", self._rewrite_cookie(c)))

                await send(
                    {
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": [
                            (k.encode("latin-1"), v.encode("latin-1")) for k, v in response_headers
                        ],
                    }
                )

                async for chunk in upstream_resp.aiter_bytes():
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})

        except httpx.RequestError as exc:
            await self._send_text(send, 502, f"Upstream error: {exc}")
            return

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    def _join_paths(self, a: str, b: str) -> str:
        """
        Join two URL paths ensuring a single slash separator.

        Args:
            a: Base path (e.g., upstream prefix).
            b: Request path from scope.

        Returns:
            The joined path string.
        """
        if not a.endswith("/"):
            a += "/"
        return a + b.lstrip("/")

    def _extract_request_headers(self, scope: Scope) -> dict[str, str]:
        """
        Extracts and sanitizes request headers from the ASGI scope.

        Drops hop-by-hop headers and those configured in
        `drop_request_headers`, applies `extra_request_headers`,
        and sets appropriate `X-Forwarded-*` headers.

        Args:
            scope: The ASGI scope containing raw request headers.

        Returns:
            A dictionary of prepared headers for the upstream request.
        """
        hdrs = {}
        for raw_k, raw_v in scope.get("headers", []):
            k = raw_k.decode("latin-1")
            v = raw_v.decode("latin-1")
            if k.lower() in self._hop_by_hop or k.lower() in self._drop_req_headers:
                continue
            hdrs[k] = v

        # Extra request headers
        hdrs.update(self._extra_req_headers)

        # Host handling
        if not self._preserve_host:
            hdrs["host"] = self._base.host or hdrs.get("host", "")

        # X-Forwarded-*
        client_addr = scope.get("client")
        client_ip = client_addr[0] if client_addr else ""
        xfwd = hdrs.get("x-forwarded-for")
        hdrs["x-forwarded-for"] = (
            (f"{xfwd}, {client_ip}" if xfwd else client_ip) if client_ip else (xfwd or "")
        )
        hdrs["x-forwarded-proto"] = "https" if scope.get("scheme") == "https" else "http"
        hdrs["x-forwarded-host"] = hdrs.get("host", "")

        return hdrs

    def _filter_response_headers(
        self, headers: Iterable[tuple[str, str]]
    ) -> list[tuple[str, str]]:
        """
        Optionally rewrites the domain in `Set-Cookie` headers.

        Uses the `rewrite_set_cookie_domain` callback if provided.
        Supports removing, modifying, or adding domains.

        Args:
            set_cookie_value: The raw `Set-Cookie` header value.

        Returns:
            The rewritten `Set-Cookie` header string.
        """
        out: list[tuple[str, str]] = []
        for k, v in headers:
            lk = k.lower()
            if lk in self._hop_by_hop or lk in self._drop_resp_headers:
                continue
            # Let ASGI server set Transfer-Encoding/Content-Length as needed
            if lk in ("transfer-encoding",):
                continue
            out.append((k, v))
        return out

    def _rewrite_cookie(self, set_cookie_value: str) -> str:
        """
        Optionally rewrites the domain in `Set-Cookie` headers.

        Uses the `rewrite_set_cookie_domain` callback if provided.
        Supports removing, modifying, or adding domains.

        Args:
            set_cookie_value: The raw `Set-Cookie` header value.

        Returns:
            The rewritten `Set-Cookie` header string.
        """
        if self._rewrite_cookie_domain is None:
            return set_cookie_value

        decision = self._rewrite_cookie_domain(set_cookie_value)
        if decision is None:
            return set_cookie_value

        parts = [p for p in (x.strip() for x in set_cookie_value.split(";")) if p]
        out = []
        domain_seen = False
        for p in parts:
            if p.lower().startswith("domain="):
                domain_seen = True
                if decision == "":
                    continue
                else:
                    out.append(f"Domain={decision}")
            else:
                out.append(p)

        # If no Domain was present and decision is to set one, add it.
        if not domain_seen and decision not in (None, ""):
            out.append(f"Domain={decision}")

        return "; ".join(out)

    async def not_found(self, send: Send) -> None:
        """
        Send a simple 404 Not Found response.

        Args:
            send: ASGI send function.
        """
        await self._send_text(send, 404, "Not Found")

    async def _send_text(self, send: Send, status: int, text: str) -> None:
        """
        Send a plain-text HTTP response.

        Args:
            send: ASGI send function.
            status: HTTP status code to send.
            text: Response body text.
        """
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": text.encode("utf-8")})
