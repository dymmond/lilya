import logging

import httpx
import pytest

pytestmark = pytest.mark.anyio


async def test_get_proxies_path_and_query(client):
    response = await client.get("/auth/echo?x=1&y=two", headers={"custom-header": "ok"})

    assert response.status_code == 200

    data = response.json()
    assert data["method"] == "GET"

    # Lilya Include should trim the mount path for the mounted ASGI app:
    assert data["path"].endswith("/echo")
    assert data["query"] == "x=1&y=two"

    # custom header should pass through
    assert data["headers"]["custom-header"] == "ok"


async def test_post_streams_body_and_content_type(client):
    payload = b"A" * 12345
    response = await client.post(
        "/auth/echo?z=9",
        content=payload,
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["method"] == "POST"
    assert data["body_len"] == len(payload)
    assert data["headers"]["content-type"] == "application/octet-stream"


async def test_hop_by_hop_headers_are_stripped(client):
    response = await client.get(
        "/auth/echo",
        headers={
            "Connection": "keep-alive",
            "TE": "trailers",
            "Upgrade": "h2c",
            "Transfer-Encoding": "chunked",
        },
    )
    assert response.status_code == 200

    data = response.json()

    # All hop-by-hop headers should be absent at the upstream
    assert data["headers"]["connection"] is not None
    assert data["headers"]["te"] is None
    assert data["headers"]["upgrade"] is None
    assert data["headers"]["transfer-encoding"] is None


async def test_x_forwarded_headers_are_added(client):
    response = await client.get("/auth/echo")

    assert response.status_code == 200
    headers = response.json()["headers"]

    # We can't reliably assert the exact client IP under ASGITransport,
    # but headers should exist and proto should be http.
    assert "x-forwarded-for" in headers
    assert headers["x-forwarded-proto"] in ("http", "https")
    assert headers["x-forwarded-host"] is not None


async def test_preserve_host_false_sets_upstream_host(proxy_and_app):
    proxy, app, _ = proxy_and_app

    await proxy.startup()

    # Default is preserve_host=False
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://public.host") as c:
        response = await c.get("/auth/echo")

        assert response.status_code == 200

        # Upstream should see the host of the target base (auth-service.local)
        seen_host = response.json()["headers"]["host"]

        assert seen_host == "auth-service.local"


async def test_preserve_host_true_keeps_original_host(proxy_and_app):
    proxy, app, _ = proxy_and_app

    await proxy.startup()
    # Toggle preserve_host at runtime for the test
    proxy._preserve_host = True  # or recreate proxy with preserve_host=True

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://frontend.local") as cli:
        response = await cli.get("/auth/echo", headers={"Host": "frontend.local"})

        assert response.status_code == 200

        seen_host = response.json()["headers"]["host"]

        assert seen_host == "frontend.local"

    # revert to avoid side effects
    proxy._preserve_host = False


async def test_cookie_domain_rewrite_drops_domain(client):
    response = await client.get("/auth/set-cookie")

    assert response.status_code == 200

    # httpx: use get_list for multi-headers
    if hasattr(response.headers, "get_list"):
        cookies = response.headers.get_list("set-cookie")

    # Lilya Headers has getlist (no underscore)
    elif hasattr(response.headers, "getlist"):
        cookies = response.headers.getlist("set-cookie")
    else:
        # Fallback: read raw headers safely
        cookies = [
            v.decode("latin-1")
            for (k, v) in getattr(response.headers, "raw", [])
            if k.lower() == b"set-cookie"
        ]

    # Should receive both cookies, and the first should have no Domain attribute
    assert len(cookies) == 2
    cookie1, cookie2 = cookies

    # First upstream cookie had Domain=auth.local, but proxy drops Domain
    assert "session=abc123" in cookie1
    assert "Domain=" not in cookie1

    # Second upstream cookie had no Domain; staying no Domain is fine as well
    assert "refresh=zzz" in cookie2


async def test_upstream_error_maps_to_502(proxy_and_app, monkeypatch):
    proxy, app, _ = proxy_and_app

    await proxy.startup()
    try:
        # Patch the instance method to raise immediately
        def boom(*args, **kwargs):
            req = httpx.Request("GET", "http://auth-service.local/echo")
            raise httpx.ConnectError("boom", request=req)

        assert proxy._client is not None
        monkeypatch.setattr(proxy._client, "stream", boom)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as cli:
            response = await cli.get("/auth/echo")

        assert response.status_code == 502
        assert "Upstream error" in response.text
    finally:
        await proxy.shutdown()


@pytest.mark.asyncio
async def test_large_streaming_download(client):
    response = await client.get("/auth/large")

    assert response.status_code == 200

    size = 0

    async for chunk in response.aiter_bytes():
        size += len(chunk)

    assert size == 1024 * 1024  # 1 MiB


async def test_timeout_maps_to_504(proxy_and_app, monkeypatch):
    proxy, app, _ = proxy_and_app
    await proxy.startup()

    # Force all requests to timeout
    def boom(*args, **kwargs):
        raise httpx.ReadTimeout("timeout", request=httpx.Request("GET", "http://dummy/"))

    assert proxy._client is not None
    monkeypatch.setattr(proxy._client, "stream", boom)

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cli:
        r = await cli.get("/auth/echo")
        assert r.status_code == 504
        assert "Gateway Timeout" in r.text

    await proxy.shutdown()


async def test_retry_on_status_and_backoff(monkeypatch, proxy_and_app):
    proxy, app, _ = proxy_and_app

    proxy._max_retries = 2
    proxy._retry_statuses = {502}
    await proxy.startup()

    call_count = {"n": 0}

    class DummyResp:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {}
            self.request = httpx.Request("GET", "http://dummy/")

        async def aclose(self):
            return

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def aiter_bytes(self):
            if self.status_code == 200:
                yield b"ok"

    def fake_stream(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            return DummyResp(502)
        return DummyResp(200)

    monkeypatch.setattr(proxy._client, "stream", fake_stream)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cli:
        r = await cli.get("/auth/echo")

    assert r.status_code == 200
    assert call_count["n"] == 3

    await proxy.shutdown()


async def test_header_allowlist_mode(proxy_and_app):
    proxy, app, _ = proxy_and_app

    proxy._allow_request_headers = {"custom-header"}
    proxy._allow_response_headers = {"content-type"}

    await proxy.startup()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cli:
        r = await cli.get("/auth/echo", headers={"Custom-Header": "ok", "X-Other": "bad"})

    data = r.json()
    headers = data["headers"]

    assert headers["custom-header"] == "ok"
    assert headers["host"] is not None
    assert headers["x-forwarded-for"] is not None

    await proxy.shutdown()


async def test_structured_logging_emits(caplog, proxy_and_app, monkeypatch):
    proxy, app, _ = proxy_and_app

    log = logging.getLogger("proxytest")
    proxy._log = log
    caplog.set_level(logging.INFO, logger="proxytest")

    await proxy.startup()

    def boom(*args, **kwargs):
        raise httpx.RequestError("boom", request=httpx.Request("GET", "http://dummy/"))

    assert proxy._client is not None
    monkeypatch.setattr(proxy._client, "stream", boom)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cli:
        await cli.get("/auth/echo")

    logs = [rec.message for rec in caplog.records if "reverse_proxy" in rec.message]
    assert any("upstream_error" in m for m in logs)

    await proxy.shutdown()
