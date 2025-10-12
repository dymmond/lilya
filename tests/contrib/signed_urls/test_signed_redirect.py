from urllib.parse import parse_qs, urlparse

import pytest

from lilya.apps import Lilya
from lilya.contrib.security.signed_urls import SignedRedirect, SignedURLGenerator
from lilya.dependencies import Provide, Provides
from lilya.responses import RedirectResponse
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def signer():
    return SignedURLGenerator(secret_key="redirect-secret")


def test_signed_redirect_creates_valid_signed_url(signer):
    redirect = SignedRedirect(url="https://example.com/dashboard", signer=signer, expires_in=300)

    assert isinstance(redirect, RedirectResponse)
    assert redirect.status_code in (302, 307)
    assert "Location" in redirect.headers

    target = redirect.headers["Location"]
    assert "sig=" in target
    assert "expires=" in target
    assert signer.verify(target)


def test_signed_redirect_preserves_query_parameters(signer):
    redirect = SignedRedirect(
        url="https://example.com/dashboard?next=/home&lang=en", signer=signer, expires_in=60
    )

    location = redirect.headers["Location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)

    assert query["next"] == ["/home"]
    assert query["lang"] == ["en"]
    assert "sig" in query and "expires" in query
    assert signer.verify(location)


def test_signed_redirect_signature_differs_with_expiration(signer):
    redirect1 = SignedRedirect("https://example.com/path", signer, expires_in=10)
    redirect2 = SignedRedirect("https://example.com/path", signer, expires_in=60)

    loc1 = redirect1.headers["Location"]
    loc2 = redirect2.headers["Location"]

    assert loc1 != loc2  # signatures differ due to expiry timestamp


def test_signed_redirect_with_different_signers():
    s1 = SignedURLGenerator("first")
    s2 = SignedURLGenerator("second")
    r1 = SignedRedirect("https://example.com/path", s1, expires_in=100)
    r2 = SignedRedirect("https://example.com/path", s2, expires_in=100)

    loc1 = r1.headers["Location"]
    loc2 = r2.headers["Location"]

    assert loc1 != loc2
    assert s1.verify(loc1)
    assert not s1.verify(loc2)
    assert s2.verify(loc2)


def test_signed_redirect_expired_is_invalid():
    signer = SignedURLGenerator("secret")
    redirect = SignedRedirect("https://example.com/old", signer, expires_in=0)
    url = redirect.headers["Location"]

    assert signer.verify(url) is False


def test_signed_redirect_works_inside_dependency_injection(monkeypatch):
    """Simulate using SignedRedirect within a Lilya dependency context."""

    signer = SignedURLGenerator("dep-secret")

    async def redirect_endpoint(signer=Provides()):
        return SignedRedirect("https://example.com/profile", signer, expires_in=120)

    app = Lilya(
        dependencies={"signer": Provide(lambda: signer)},
        routes=[Path("/redir", redirect_endpoint)],
    )

    client = TestClient(app, follow_redirects=False)
    res = client.get("/redir")

    assert res.status_code in (302, 307)

    loc = res.headers["Location"]
    assert signer.verify(loc)


def test_signed_redirect_custom_status_code(signer):
    redirect = SignedRedirect("https://example.com/custom", signer, expires_in=60)

    # Ensure inherits Redirect behavior (default 307)
    assert redirect.status_code == 307
    assert redirect.headers["Location"].startswith("https://example.com/custom")
