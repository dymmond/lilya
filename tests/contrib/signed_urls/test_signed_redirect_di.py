import pytest

from lilya.apps import Lilya
from lilya.contrib.security.signed_urls import SignedRedirect, SignedURLGenerator
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


def test_signed_url_generator_injection_global_scope():
    """
    Verify that SignedURLGenerator can be provided and injected globally.
    """

    async def redirect_endpoint(signer=Provides()):
        url = "https://example.com/resource"
        signed_url = signer.sign(url, expires_in=10)
        return {"signed_url": signed_url, "valid": signer.verify(signed_url)}

    signer = SignedURLGenerator(secret_key="global-secret")

    app = Lilya(
        dependencies={"signer": Provide(lambda: signer, scope="GLOBAL")},
        routes=[Path("/sign", redirect_endpoint)],
    )

    client = TestClient(app)
    response = client.get("/sign")
    body = response.json()

    assert response.status_code == 200
    assert body["valid"] is True
    assert "sig=" in body["signed_url"]
    assert "expires=" in body["signed_url"]


def test_signed_redirect_with_injected_signer():
    """
    Ensure SignedRedirect works correctly when the signer is injected
    via dependency injection.
    """

    signer = SignedURLGenerator(secret_key="dep-secret")

    async def redirect_endpoint(signer=Provides()):
        return SignedRedirect("https://example.com/profile", signer, expires_in=120)

    app = Lilya(
        dependencies={"signer": Provide(lambda: signer, scope="GLOBAL")},
        routes=[Path("/redir", redirect_endpoint)],
    )

    client = TestClient(app, follow_redirects=False)
    res = client.get("/redir")

    assert res.status_code in (302, 307)
    location = res.headers["Location"]

    assert "sig=" in location
    assert "expires=" in location
    assert signer.verify(location)


def test_signed_redirect_reuses_same_signer_instance():
    created = []

    def factory():
        signer = SignedURLGenerator(secret_key="reused-secret")
        created.append(signer)
        return signer

    async def endpoint(signer=Provides()):
        signed_url = signer.sign("https://example.com/item", expires_in=60)
        return {"signed_url": signed_url}

    app = Lilya(
        dependencies={"signer": Provide(factory, scope="GLOBAL")},
        routes=[Path("/item", endpoint)],
    )

    with TestClient(app) as client:
        res1 = client.get("/item")
        res2 = client.get("/item")

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert len(created) == 1  # GLOBAL scope ensures reuse


def test_signed_redirect_independent_per_app_scope():
    """
    Check that APP scope produces new instances per app mount.
    """

    created = []

    def factory():
        signer = SignedURLGenerator(secret_key="app-secret")
        created.append(signer)
        return signer

    async def endpoint(signer=Provides()):
        signed = signer.sign("https://example.com/app", expires_in=30)
        return {"signed": signed}

    sub1 = Lilya(
        dependencies={"signer": Provide(factory, scope="APP")}, routes=[Path("/a", endpoint)]
    )
    sub2 = Lilya(
        dependencies={"signer": Provide(factory, scope="APP")}, routes=[Path("/b", endpoint)]
    )

    # Two separate apps, should create two signers
    client1 = TestClient(sub1)
    client2 = TestClient(sub2)

    client1.get("/a")
    client2.get("/b")

    assert len(created) == 2
    assert created[0] is not created[1]


def test_signed_redirect_with_different_scopes():
    call_counts = {"global": 0, "request": 0}

    def global_factory():
        call_counts["global"] += 1
        return SignedURLGenerator(secret_key="global-secret")

    def request_factory():
        call_counts["request"] += 1
        return SignedURLGenerator(secret_key="request-secret")

    async def endpoint(global_signer=Provides(), req_signer=Provides()):
        u1 = global_signer.sign("https://example.com/a", expires_in=30)
        u2 = req_signer.sign("https://example.com/b", expires_in=30)
        return {"valid1": global_signer.verify(u1), "valid2": req_signer.verify(u2)}

    app = Lilya(
        dependencies={
            "global_signer": Provide(global_factory, scope="GLOBAL"),
            "req_signer": Provide(request_factory, scope="REQUEST"),
        },
        routes=[Path("/multi", endpoint)],
    )

    with TestClient(app) as client:
        for _ in range(3):
            r = client.get("/multi")
            assert r.status_code == 200
            data = r.json()
            assert data["valid1"]
            assert data["valid2"]

    assert call_counts["global"] == 1  # one per GLOBAL
    assert call_counts["request"] == 3  # one per REQUEST
