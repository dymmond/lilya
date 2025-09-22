import asyncio
import json

import httpx
import pytest

from lilya.apps import Lilya
from lilya.contrib.proxy.reverse import Relay
from lilya.routing import Include


class DummyUpstream:
    """
    Minimal ASGI app to act as the upstream service.

    Routes:
      - GET/POST /echo      : echoes method, path, query, headers subset, body
      - GET /set-cookie     : sets cookies
      - GET /large          : streams a large body
    """

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._respond_text(send, 404, "Not Found")
            return

        method = scope["method"]
        path = scope.get("path", "/")
        query_bytes: bytes = scope.get("query_string", b"")
        query = query_bytes.decode("latin-1") if query_bytes else ""

        headers = {}
        for k, v in scope.get("headers", []):
            headers[k.decode("latin-1")] = v.decode("latin-1")

        # Collect body if present
        body_chunks: list[bytes] = []
        more = True
        while more:
            event = await receive()
            if event["type"] == "http.request":
                body = event.get("body", b"")
                if body:
                    body_chunks.append(body)
                more = event.get("more_body", False)
            elif event["type"] == "http.disconnect":
                break

        if path.endswith("/echo"):
            await self._respond_json(
                send,
                200,
                {
                    "method": method,
                    "path": path,
                    "query": query,
                    "headers": {
                        # Echo a subset we care about in tests
                        "host": headers.get("host"),
                        "x-forwarded-for": headers.get("x-forwarded-for"),
                        "x-forwarded-proto": headers.get("x-forwarded-proto"),
                        "x-forwarded-host": headers.get("x-forwarded-host"),
                        "connection": headers.get("connection"),
                        "te": headers.get("te"),
                        "upgrade": headers.get("upgrade"),
                        "transfer-encoding": headers.get("transfer-encoding"),
                        "custom-header": headers.get("custom-header"),
                        "content-type": headers.get("content-type"),
                    },
                    "body_len": sum(len(c) for c in body_chunks),
                },
            )
            return

        if path.endswith("/set-cookie"):
            cookies = [
                # Upstream sets a cookie with Domain we will rewrite
                "session=abc123; Path=/; HttpOnly; Domain=auth.local; SameSite=Lax",
                # And another without Domain
                "refresh=zzz; Path=/; Secure; SameSite=None",
            ]
            await self._respond_text(
                send,
                200,
                "ok",
                extra_headers=[(b"set-cookie", c.encode("latin-1")) for c in cookies],
            )
            return

        if path.endswith("/large"):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/octet-stream")],
                }
            )
            # Stream 1MB in chunks
            chunk = b"x" * 65536
            for _ in range(16):  # 16 * 64KiB = 1 MiB
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
                # Yield control
                await asyncio.sleep(0)
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        await self._respond_text(send, 404, "Not Found")

    async def _respond_text(
        self, send, status: int, text: str, *, extra_headers: list[tuple[bytes, bytes]] = None
    ):
        headers = [(b"content-type", b"text/plain; charset=utf-8")]
        if extra_headers:
            headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": text.encode("utf-8")})

    async def _respond_json(self, send, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": data})


@pytest.fixture
def upstream_app():
    return DummyUpstream()


@pytest.fixture
def proxy_and_app(upstream_app):
    """
    Builds the proxy (targeting `upstream_app`) and a Lilya app mounting it at /auth using Include.
    Starts the proxy client on fixture entry and closes on exit.
    Returns (proxy, app).
    """
    # Target base is a dummy schema+host; httpx's ASGITransport ignores the host and uses the ASGI app.
    # We'll pass upstream_app via transport on the client—we only need a URL with a path to join.
    target_base = "http://auth-service.local"

    upstream_transport = httpx.ASGITransport(app=upstream_app)
    proxy = Relay(
        target_base_url=target_base,
        upstream_prefix="/",  # map /auth/<path> -> /<path> on upstream
        preserve_host=False,
        rewrite_set_cookie_domain=lambda original: "",
        transport=upstream_transport,
    )

    # Build Lilya app with Include
    app = Lilya(
        routes=[
            Include("/auth", app=proxy),
        ],
        on_startup=[proxy.startup],
        on_shutdown=[proxy.shutdown],
    )

    return proxy, app, upstream_app


@pytest.fixture
async def client(proxy_and_app):
    """
    Provides an httpx.AsyncClient wired to the Lilya app and ensures the proxy lifecycle runs.
    """
    proxy, app, upstream_app = proxy_and_app

    # Manually run proxy startup since ASGITransport won't trigger app lifespan automatically
    await proxy.startup()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await proxy.shutdown()
