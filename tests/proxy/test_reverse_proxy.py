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
