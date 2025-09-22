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


class Relay:
    """
    ASGI relay middleware for Lilya.

    This component forwards incoming ASGI requests to an upstream server
    using `httpx.AsyncClient` and streams the response back to the caller.

    Key features
    ------------
    - **HTTP proxying** with streaming request and response bodies.
    - **WebSocket proxying** (optional, requires the `websockets` package).
    - **Header management**: filters hop-by-hop headers, supports drop/allow lists,
      and injects `X-Forwarded-*` headers automatically.
    - **Cookie rewriting**: can modify or remove the `Domain` attribute on
      `Set-Cookie` headers via a callback.
    - **Retry policy**: supports retries on network exceptions or retryable
      status codes with exponential backoff.
    - **Structured logging**: emits one log entry per retry, timeout, or error
      with event type and key/value metadata.

    Typical usage
    -------------
    ```python
    proxy = Relay("http://upstream.local", upstream_prefix="/api")

    app = Lilya(routes=[Include("/proxy", app=proxy)])

    @app.on_startup
    async def open():
        await proxy.startup()

    @app.on_shutdown
    async def close():
        await proxy.shutdown()
    ```
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
        """
        Initialize the proxy's underlying HTTP client.

        Creates a persistent `httpx.AsyncClient` with the configured
        timeouts, connection limits, redirect behavior, and (optionally)
        a custom transport. This must be called before the proxy can
        forward any HTTP requests.

        Typically, you register this in the application’s
        `on_startup` event so the client is ready before handling traffic.

        Example:
            app = Lilya(
                routes=[Include("/auth", app=proxy)],
                on_startup=[proxy.startup],
                on_shutdown=[proxy.shutdown],
            )
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
        Dispose of the underlying HTTP client.

        Closes the internal `httpx.AsyncClient`, releasing all
        connection pool resources and preventing further requests.
        After shutdown, the proxy cannot handle HTTP traffic until
        `startup()` is called again.

        Typically, you register this in the application’s
        `on_shutdown` event to ensure a clean shutdown.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI entrypoint for the relay.

        This method is invoked by the ASGI server whenever a new
        connection is routed to the proxy. It inspects the `scope["type"]`
        and dispatches accordingly:

            - `"http"` → forwards the request via `_handle_http`.
            - `"websocket"` → proxies the connection via `_handle_websocket`.
            - Any other type → responds with a `404 Not Found`.

        Args:
            scope: The ASGI connection scope (contains type, path, headers, etc.).
            receive: The ASGI receive callable, used to await incoming events.
            send: The ASGI send callable, used to send response or WS events.

        Raises:
            AssertionError: If the proxy was not started with `startup()`
            before being invoked.

        Example:
            When mounted at `/auth`:

                app = Lilya(routes=[Include("/auth", app=Relay(...))])

            The ASGI server will call `proxy(scope, receive, send)` whenever
            a request matches the `/auth` prefix.
        """
        scope_type = scope["type"]

        if scope_type == "http":
            await self._handle_http(scope, receive, send)
        elif scope_type == "websocket":
            await self._handle_websocket(scope, receive, send)
        else:
            await self._send_text(send, 404, "Not Found")

        assert self._client is not None, "Relay not started. Call startup() first."

    async def _handle_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Forward an incoming HTTP request to the configured upstream.

        This method builds the upstream URL and request headers from the ASGI
        scope, streams the request body if present, and relays the response
        headers and body back to the client.

        Retry behavior:
          - **Timeouts** are mapped to 504 Gateway Timeout.
          - **Retryable statuses** (e.g. 502, 503, 504) raise `HTTPStatusError`
            and trigger exponential backoff until `max_retries` is exceeded.
          - **Retryable exceptions** (e.g. `httpx.ConnectError`) are retried
            with backoff.
          - Other `httpx.RequestError`s are returned immediately as 502.

        Args:
            scope: The ASGI connection scope for the request.
            receive: Coroutine that yields request events.
            send: Coroutine used to send response events.

        Side effects:
            Emits structured logs for retries, timeouts, and errors.
        """
        assert self._client is not None, "Relay not started. Call startup() first."

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
        """
        Calculate the backoff delay before the next retry attempt.

        Implements an exponential backoff algorithm:

            delay = retry_backoff_factor * (2 ** (attempt - 1))

        Where:
            - `retry_backoff_factor` is a base multiplier (e.g. 0.2s).
            - `attempt` is the current retry number, starting at 1.

        Example:
            With `retry_backoff_factor=0.2`:
                attempt=1 → 0.2s
                attempt=2 → 0.4s
                attempt=3 → 0.8s
                attempt=4 → 1.6s

        Args:
            attempt: The current retry attempt number (1-based).

        Returns:
            The number of seconds to wait before retrying, as a float.
        """
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
        """
        Construct the full upstream URL for a given ASGI request.

        This method takes the incoming request path and query string
        from the ASGI `scope`, joins it with the configured upstream
        prefix, and combines it with the proxy’s base URL.

        Behavior:
            - Uses `scope["raw_path"]` if available, otherwise falls back
              to `scope["path"]`.
            - Decodes the path from bytes to a UTF-8 string.
            - Joins the path with `self._upstream_prefix` via `_join_paths`.
            - Preserves the raw query string.

        Args:
            scope: The ASGI connection scope containing request metadata.

        Returns:
            An `httpx.URL` object representing the target upstream URL.

        Example:
            If base_url="http://auth.local", upstream_prefix="/api", and
            the client requests "/auth/echo?x=1":

                Result → http://auth.local/api/echo?x=1
        """
        raw_path: bytes = scope.get("raw_path", scope["path"].encode("latin-1"))
        query_string: bytes = scope.get("query_string", b"")
        path = raw_path.decode("latin-1")
        upstream_path = self._join_paths(self._upstream_prefix, path)
        return self._base_url.join(upstream_path).copy_with(query=query_string)

    def _prepare_request_headers(self, scope: Scope) -> dict[str, str]:
        """
        Build the set of headers to forward to the upstream server.

        This method normalizes request headers, strips hop-by-hop or
        explicitly dropped headers, optionally overrides the `Host`
        header, and injects standard `X-Forwarded-*` headers so the
        upstream can see the original client context.

        Behavior:
            - Iterates through `scope["headers"]` and decodes keys/values
              to strings.
            - Removes hop-by-hop headers (Connection, TE, Upgrade, etc.).
            - Removes any headers configured in `_drop_request_headers`.
            - Adds any extra headers from `_extra_request_headers`.
            - If `preserve_host` is False, rewrites the `Host` header to
              match the upstream base URL.
            - Ensures `x-forwarded-for`, `x-forwarded-proto`, and
              `x-forwarded-host` are always present.

        Args:
            scope: The ASGI connection scope for the incoming request.

        Returns:
            A dictionary of header names and values safe to forward.

        Example:
            Input headers:
                {"Host": "frontend.local", "Connection": "keep-alive"}

            Output headers (preserve_host=False):
                {
                  "Host": "auth.local",
                  "x-forwarded-for": "127.0.0.1",
                  "x-forwarded-proto": "http",
                  "x-forwarded-host": "auth.local"
                }
        """
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
        """
        Create an async generator that streams the request body from ASGI events.

        This helper wraps the ASGI `receive` callable in an async generator
        that yields body chunks as they arrive from the client. It allows the
        proxy to forward request bodies (e.g. file uploads, large JSON payloads)
        to the upstream without buffering the entire request in memory.

        Behavior:
            - Yields each non-empty `body` field from `http.request` events.
            - Continues until `more_body` is False, meaning the client has sent
              the complete request body.
            - If a `http.disconnect` event is received, iteration stops early.

        Args:
            receive: The ASGI `receive` callable for this connection.

        Returns:
            An async iterator of `bytes` chunks representing the request body.

        Example:
            >>> async for chunk in proxy._build_request_body_stream(receive):
            ...     print(len(chunk))
            8192
            8192
            1024
        """

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
        """
        Perform a single upstream HTTP request and relay the response.

        Opens a streaming request to the upstream server using httpx and
        forwards the response headers and body to the client.

        - If the status code is in `retry_statuses`, raises
          `httpx.HTTPStatusError` to trigger the retry loop.
        - If `rewrite_set_cookie_domain` is provided, rewrites `Set-Cookie`
          headers before sending them back.
        - Streams response body in chunks to avoid buffering large payloads.

        Raises:
            httpx.HTTPStatusError: For retryable statuses.
            httpx.RequestError: For network or protocol errors.
        """

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
        Proxy a WebSocket connection to the upstream server.

        Accepts the downstream WebSocket, opens a new upstream WebSocket using
        the `websockets` library, and shuttles messages bidirectionally until
        either side closes.

        Behavior:
          - Converts http/https upstream base to ws/wss.
          - Forwards both text and binary frames.
          - If the `websockets` package is not installed, responds with 1011
            (server error, close).
          - On upstream timeout, closes with 1011 and reason "Upstream WS timeout".
          - On other errors, closes with 1011 and logs the exception.

        Args:
            scope: ASGI WebSocket scope.
            receive: Coroutine yielding WebSocket events from the client.
            send: Coroutine to send WebSocket events back to the client.
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
        Relay WebSocket messages bidirectionally between client and upstream.

        This method runs two concurrent tasks inside an `anyio.TaskGroup`:

        - **downstream_to_upstream**:
          Reads ASGI `websocket.receive` events from the client and forwards
          them to the upstream WebSocket connection. Supports both text and
          binary frames. On `websocket.disconnect`, attempts to close the
          upstream gracefully and stops the loop.

        - **upstream_to_downstream**:
          Iterates messages coming from the upstream WebSocket connection and
          forwards them as ASGI `websocket.send` events to the client. If the
          upstream closes, sends a final `websocket.close` frame with code
          `1000` (normal closure).

        Args:
            scope: The ASGI scope for this connection (not directly used here,
                but passed for consistency).
            receive: ASGI receive callable that yields client events.
            send: ASGI send callable used to emit messages back to the client.
            upstream: An open WebSocket connection object from the
                `websockets` library.

        Behavior:
            - Both tasks run until one side closes the connection.
            - Ensures resources are cleaned up properly even if one side
              disconnects abruptly.
            - Uses `anyio.create_task_group` for concurrency, making it
              backend-agnostic (works with asyncio or trio).

        Example:
            Client <──text──> Proxy <──text──> Upstream
            Client <──bytes─> Proxy <──bytes─> Upstream

        Close codes:
            - 1000: Normal closure when upstream ends.
            - 1011: Internal error (sent by `_handle_websocket` on exceptions).
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
        Build the upstream WebSocket URL from the ASGI scope.

        Converts the base upstream HTTP(S) URL into the equivalent
        WebSocket scheme (`ws://` or `wss://`) and appends the request
        path and query string. This ensures that WebSocket connections
        are routed to the correct upstream endpoint.

        Args:
            scope: The ASGI WebSocket scope containing the connection
                details such as `scheme`, `path`, and `query_string`.

        Returns:
            A fully-qualified `httpx.URL` pointing to the upstream WebSocket.

        Example:
            If the proxy is configured with base_url="http://upstream.local"
            and the client connects to:

                ws://proxy.local/chat?room=1

            Then this method will generate:

                ws://upstream.local/chat?room=1
        """

        scheme = scope.get("scheme", "http")
        ws_scheme = "wss" if scheme == "https" else "ws"
        http_equiv = self._build_upstream_url(scope)  # includes joined path + query
        return http_equiv.copy_with(scheme=ws_scheme)

    async def _send_ws_close(self, send: Send, code: int, reason: str) -> None:
        """
        Send a WebSocket close event downstream.

        Used when the proxy needs to terminate a WebSocket session
        due to an upstream timeout, error, or orderly shutdown.
        Wraps the ASGI `websocket.close` message.

        Args:
            send: The ASGI `send` callable used to emit events.
            code: WebSocket close code (e.g. 1000 for normal close,
                1011 for internal error).
            reason: Optional human-readable reason string describing
                why the connection was closed.

        ASGI Message Sent:
            ```python
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
            ```
        Example:

            >>> await proxy._send_ws_close(send, 1011, "Upstream WS timeout")
        """

        await send({"type": "websocket.close", "code": code, "reason": reason})

    def _sanitize_response_headers(
        self, headers: Iterable[tuple[str, str]]
    ) -> list[tuple[str, str]]:
        """
        Filter upstream response headers before sending them downstream.

        Some HTTP headers are considered *hop-by-hop* and must never be
        forwarded by proxies (e.g. `Connection`, `Keep-Alive`). This method
        removes those as well as any headers explicitly marked for dropping
        in the proxy configuration.

        Behavior:
            - Iterates over all headers returned by the upstream.
            - Excludes hop-by-hop headers defined in `_hop_by_hop_headers`.
            - Excludes any headers listed in `_drop_response_headers`.
            - Explicitly strips `Transfer-Encoding` headers since streaming
              is managed by ASGI.

        Args:
            headers: Iterable of (name, value) header pairs from the upstream
                response.

        Returns:
            A list of (name, value) pairs safe to include in the downstream
            response.

        Example:
            Input:
                [("Content-Type", "text/plain"),
                 ("Connection", "keep-alive"),
                 ("X-Custom", "yes")]

            Output:
                [("Content-Type", "text/plain"),
                 ("X-Custom", "yes")]
        """
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
        """
        Process and potentially rewrite all `Set-Cookie` headers from an upstream response.

        This method is only active when a `rewrite_set_cookie_domain` callback
        was provided to the proxy. It inspects the upstream response headers,
        extracts all `Set-Cookie` values, and passes each one through
        `_rewrite_cookie` to apply domain rewrite rules.

        Behavior:
            - Collects all cookies from `response.headers`.
            - Removes any existing `Set-Cookie` entries from the `headers` list.
            - Re-appends rewritten cookies based on the callback’s logic.
            - If no cookies are present, returns headers unchanged.

        Args:
            response: The upstream `httpx.Response` object whose headers may
                contain one or more `Set-Cookie` fields.
            headers: The current header list destined for the downstream client.

        Returns:
            A new header list where all `Set-Cookie` headers have been
            rewritten (or dropped) according to `_rewrite_cookie`.

        Example:
            If upstream sets a cookie:
                Set-Cookie: session=abc; Path=/; Domain=auth.local

            And the callback maps all domains to "example.com",
            the downstream response will include:
                Set-Cookie: session=abc; Path=/; Domain=example.com
        """
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
        """
        Rewrite the `Domain` attribute of a Set-Cookie header value.

        This uses the `rewrite_set_cookie_domain` callback provided at proxy
        initialization. The callback decides how the cookie domain should be
        handled for downstream clients.

        Behavior:
            - If no callback is configured, the cookie is returned unchanged.
            - If the callback returns `None`, the cookie is returned unchanged.
            - If the callback returns an empty string (""), any existing Domain
              attribute is dropped.
            - If the callback returns a non-empty string, the Domain attribute
              is set to that value (replacing any existing Domain).

        Args:
            cookie_value: Raw `Set-Cookie` header value from the upstream response.

        Returns:
            The modified `Set-Cookie` header string with the Domain attribute
            rewritten, removed, or left intact according to the callback.

        Example:
            >>> proxy._rewrite_cookie("session=abc; Path=/; Domain=auth.local")
            "session=abc; Path=/; Domain=example.com"
        """

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
        """
        Send a minimal plain-text HTTP response downstream.

        This helper is used for error cases (e.g. timeouts, upstream errors)
        where we want to quickly send a status code and a human-readable
        message without building a full response object.

        Args:
            send: The ASGI `send` callable used to emit events back to the client.
            status: The HTTP status code to send (e.g. 502, 504).
            text: The response body as a plain UTF-8 string.

        ASGI Messages Emitted:
            - `http.response.start`: starts the response with status + content type.
            - `http.response.body`: contains the encoded text payload.

        Note:
            The response is always returned with
            `Content-Type: text/plain; charset=utf-8`.
        """

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
        Emit a structured log line for proxy events.

        Log lines are prefixed with `reverse_proxy.<event>` and include all
        additional fields as `key=value` pairs.

        Example:
            reverse_proxy.upstream_timeout url='http://...' attempt=2 error='ReadTimeout(...)'

        Args:
            event: Short identifier for the event type (e.g. "upstream_timeout").
            **fields: Arbitrary key/value pairs providing context for the log.
        """
        if not self._log:
            return
        self._log.info(
            "reverse_proxy.%s %s", event, " ".join(f"{k}={v!r}" for k, v in fields.items())
        )
