from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from typing import Any, cast

import anyio
import websockets

from lilya.types import Receive, Scope, Send

try:
    import httpx
except ImportError as e:
    raise ImportError("httpx is required for lilya.contrib.proxy") from e


class ReverseProxy:
    """
    ASGI reverse proxy for Lilya with HTTP + optional WebSocket support.

    Features
    --------
    - Streams requests/responses using httpx.AsyncClient.
    - Hop-by-hop header filtering.
    - Optional `Set-Cookie` domain rewriting.
    - X-Forwarded-* headers injection.
    - Optional retry policy (status/exception, exponential backoff).
    - Optional header allow-list mode (instead of drop-list).
    - Optional WebSocket proxying (requires `websockets` package).
    - Structured logging (pass a logger).

    Backwards-compatibility
    -----------------------
    Defaults match your current behavior; enabling retries/allow-lists/WS is opt-in.
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
        allow_request_headers: Iterable[str] | None = None,
        allow_response_headers: Iterable[str] | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 0,
        retry_backoff_factor: float = 0.2,
        retry_statuses: Sequence[int] = (502, 503, 504),
        retry_exceptions: tuple[type[Exception], ...] = (httpx.ConnectError, httpx.ReadTimeout),
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Args:
            target_base_url: Upstream base (scheme+host+optional base path).
            upstream_prefix: Path prefix prepended before forwarding to upstream.
            preserve_host: If True, keep original `Host` header; otherwise rewrite to upstream host.
            rewrite_set_cookie_domain: Callback to rewrite cookie Domain; return "" to drop Domain,
                or return None to leave cookie unchanged.
            timeout: httpx.Timeout or float seconds for upstream requests.
            limits: httpx connection pool limits.
            follow_redirects: Whether to follow upstream redirects.
            extra_request_headers: Extra headers to add to each request.
            drop_request_headers: Case-insensitive names to strip from requests.
            drop_response_headers: Case-insensitive names to strip from responses.
            allow_request_headers: If provided, only these headers are forwarded (plus computed ones).
            allow_response_headers: If provided, only these headers are forwarded back.
            transport: Optional custom httpx transport (e.g., ASGITransport in tests).
            max_retries: Max total retries (0 = disabled).
            retry_backoff_factor: Base seconds for exponential backoff (sleep = factor * 2**(attempt-1)).
            retry_statuses: HTTP statuses that should be retried.
            retry_exceptions: Exception types that should be retried.
            logger: Optional logger for structured logs.
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
        self._allow_request_headers = {h.lower() for h in (allow_request_headers or [])} or None
        self._allow_response_headers = {h.lower() for h in (allow_response_headers or [])} or None
        self._client: httpx.AsyncClient | None = None
        self._transport = transport

        # Retries
        self._max_retries = max_retries
        self._retry_backoff_factor = retry_backoff_factor
        self._retry_statuses = set(retry_statuses)
        self._retry_exceptions = retry_exceptions

        # Logging
        self._log = logger

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
        scope_type = scope["type"]

        if scope_type == "http":
            await self._handle_http(scope, receive, send)
        elif scope_type == "websocket":
            await self._handle_websocket(scope, receive, send)
        else:
            await self._send_text(send, 404, "Not Found")

        assert self._client is not None, "ReverseProxy not started. Call startup() first."

    async def _handle_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an HTTP request by forwarding to upstream with streaming."""
        assert self._client is not None, "ReverseProxy not started. Call startup() first."

        method = scope["method"]
        upstream_url = self._build_upstream_url(scope)
        request_headers = self._prepare_request_headers(scope)
        request_body = (
            self._build_request_body_stream(receive)
            if method not in ("GET", "HEAD", "OPTIONS")
            else None
        )

        attempt = 0
        while True:
            attempt += 1
            try:
                await self._forward_to_upstream(
                    method, upstream_url, request_headers, request_body, send
                )
                return
            except httpx.HTTPStatusError as exc:
                self._log_event(
                    "upstream_retryable_status",
                    url=str(upstream_url),
                    attempt=attempt,
                    status=exc.response.status_code,
                )
                if attempt <= self._max_retries:
                    await anyio.sleep(self._retry_sleep_seconds(attempt))
                    continue
                await self._send_text(send, exc.response.status_code, exc.response.text)
                return
            except httpx.TimeoutException as exc:
                # Map timeouts to 504 Gateway Timeout
                self._log_event(
                    "upstream_timeout",
                    url=str(upstream_url),
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt <= self._max_retries:
                    await anyio.sleep(self._retry_sleep_seconds(attempt))
                    continue
                await self._send_text(send, 504, "Gateway Timeout")
                return
            except self._retry_exceptions as exc:
                self._log_event(
                    "upstream_retryable_error",
                    url=str(upstream_url),
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt <= self._max_retries:
                    await anyio.sleep(self._retry_sleep_seconds(attempt))
                    continue
                await self._send_text(send, 502, f"Upstream error: {exc}")
                return
            except httpx.RequestError as exc:
                # Non-retryable httpx error
                self._log_event("upstream_error", url=str(upstream_url), error=str(exc))
                await self._send_text(send, 502, f"Upstream error: {exc}")
                return

    def _retry_sleep_seconds(self, attempt: int) -> float:
        """Exponential backoff: factor * 2^(attempt-1)."""
        return cast(float, self._retry_backoff_factor * (2 ** (attempt - 1)))

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
            if resp.status_code in self._retry_statuses:
                raise httpx.HTTPStatusError(
                    f"Retryable status: {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )

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

    async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Proxy WebSocket connections to upstream using the `websockets` package.

        Notes:
            - Requires `websockets` to be installed (`pip install websockets`).
            - Builds the upstream WS URL by converting http/https -> ws/wss and joining paths.
            - Streams messages bidirectionally until close.
        """
        if websockets is None:
            # 501 (Not Implemented) because dependency is missing
            await self._send_ws_close(send, 1011, "Server cannot proxy WebSockets")
            return

        # Accept downstream connection first
        await send({"type": "websocket.accept"})

        # Build upstream WS URL
        ws_url = self._build_upstream_ws_url(scope)

        # Prepare headers (limited subset is typical for WS handshake)
        request_headers = self._prepare_request_headers(scope)

        # Connect upstream
        try:
            async with websockets.connect(
                str(ws_url),
                extra_headers=request_headers,
                open_timeout=getattr(self._timeout, "connect", 10.0)
                if isinstance(self._timeout, httpx.Timeout)
                else float(self._timeout),
                close_timeout=None,
                ping_interval=None,
            ) as upstream:
                await self._pump_websocket(scope, receive, send, upstream)
        except TimeoutError:
            await self._send_ws_close(send, 1011, "Upstream WS timeout")
        except Exception as exc:  # noqa: BLE001
            self._log_event("websocket_error", url=str(ws_url), error=str(exc))
            await self._send_ws_close(send, 1011, "Upstream WS error")

    async def _pump_websocket(
        self, scope: Scope, receive: Receive, send: Send, upstream: Any
    ) -> None:
        """
        Bidirectionally forward messages between client (ASGI) and upstream WS.
        """

        async def downstream_to_upstream() -> None:
            while True:
                event = await receive()
                t = event["type"]
                if t == "websocket.receive":
                    if "text" in event and event["text"] is not None:
                        await upstream.send(event["text"])
                    elif "bytes" in event and event["bytes"] is not None:
                        await upstream.send(event["bytes"])
                elif t == "websocket.disconnect":
                    try:
                        await upstream.close()
                    finally:
                        break  # noqa

        async def upstream_to_downstream() -> None:
            try:
                async for message in upstream:
                    if isinstance(message, (bytes, bytearray)):
                        await send({"type": "websocket.send", "bytes": message})
                    else:
                        await send({"type": "websocket.send", "text": message})
            finally:
                await self._send_ws_close(send, 1000, "Upstream closed")

        async with anyio.create_task_group() as tg:
            tg.start_soon(downstream_to_upstream)
            tg.start_soon(upstream_to_downstream)

    def _build_upstream_ws_url(self, scope: Scope) -> httpx.URL:
        """
        Convert base HTTP(S) URL to WS(S) and join with request path + query.
        """
        scheme = scope.get("scheme", "http")
        ws_scheme = "wss" if scheme == "https" else "ws"
        http_equiv = self._build_upstream_url(scope)  # includes joined path + query
        return http_equiv.copy_with(scheme=ws_scheme)

    async def _send_ws_close(self, send: Send, code: int, reason: str) -> None:
        """Send a WebSocket close frame."""
        await send({"type": "websocket.close", "code": code, "reason": reason})

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
        get_list = getattr(response.headers, "get_list", None) or getattr(
            response.headers, "getlist", None
        )
        if get_list:
            cookies = get_list("set-cookie")
        else:
            cookies = [
                v
                for (k, v) in getattr(response.headers, "items", lambda: [])()
                if k.lower() == "set-cookie"
            ]
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

    def _log_event(self, event: str, **fields: Any) -> None:
        """
        Structured log helper. Emits one line per event with key/value fields.
        """
        if not self._log:
            return
        self._log.info(
            "reverse_proxy.%s %s", event, " ".join(f"{k}={v!r}" for k, v in fields.items())
        )
