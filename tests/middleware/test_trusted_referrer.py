from collections.abc import Callable

import pytest

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedreferrer import TrustedReferrerMiddleware
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import TestClient

TestClientFactory = Callable[..., TestClient]


def test_trusted_referrer_middleware(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope["referrer_is_trusted"]
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedReferrerMiddleware,
                allowed_referrers=["testserver", "*.testserver"],
                block_untrusted_referrers=True,
            )
        ],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"referer": "http://testserver/foo/foo?test=4"})
    assert response.status_code == 200

    response = client.get("/", headers={"referer": "http://subdomain.testserver/foo/foo?test=4"})
    assert response.status_code == 200

    response = client.get("/", headers={"referer": "http://invalidhost/foo/foo?test=4"})
    assert response.status_code == 400

    # same origin
    client = test_client_factory(app, base_url="http://otherserver")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == 200


@pytest.mark.parametrize("allow_same_origin", [True, False])
def test_trusted_referrer_same_origin(
    test_client_factory: TestClientFactory, allow_same_origin: bool
) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope["referrer_is_trusted"]
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedReferrerMiddleware,
                block_untrusted_referrers=True,
                allow_same_origin=allow_same_origin,
            )
        ],
    )

    # same origin
    client = test_client_factory(app, base_url="http://otherserver")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == (200 if allow_same_origin else 400)


@pytest.mark.parametrize("allow_empty", [True, False])
def test_trusted_referrer_allow_empty(
    test_client_factory: TestClientFactory, allow_empty: bool
) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope["referrer_is_trusted"]
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedReferrerMiddleware,
                block_untrusted_referrers=True,
                allowed_referrers=["", "otherserver"] if allow_empty else ["otherserver"],
            )
        ],
    )

    client = test_client_factory(app, base_url="http://otherserver")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == 200
    response = client.get("/")
    assert response.status_code == (200 if allow_empty else 400)


def test_trusted_referrer_allow_any(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope["referrer_is_trusted"]
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedReferrerMiddleware,
                block_untrusted_referrers=True,
                allowed_referrers=["*"],
            )
        ],
    )

    client = test_client_factory(app, base_url="http://otherserver")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == 200
    response = client.get("/")
    assert response.status_code == 200

    client = test_client_factory(app, base_url="http://urlnotmattters")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == 200
    response = client.get("/")
    assert response.status_code == 200


def test_trusted_referrer_middleware_scope_only(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        return PlainText(f"{request.scope['referrer_is_trusted']}", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedReferrerMiddleware,
                allowed_referrers=["testserver", "*.testserver"],
            )
        ],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"referer": "http://testserver/foo/foo?test=4"})
    assert response.status_code == 200
    assert response.text == "True"

    response = client.get("/", headers={"referer": "http://subdomain.testserver/foo/foo?test=4"})
    assert response.status_code == 200
    assert response.text == "True"

    response = client.get("/", headers={"referer": "http://invalidhost/foo/foo?test=4"})
    assert response.status_code == 200
    assert response.text == "False"

    # same origin
    client = test_client_factory(app, base_url="http://otherserver")
    response = client.get("/", headers={"referer": "http://otherserver/foo/foo?test=4"})
    assert response.status_code == 200
    assert response.text == "True"


def test_default_allowed_referrers() -> None:
    app = Lilya()
    middleware = TrustedReferrerMiddleware(app)
    assert middleware.allowed_referrers == set()
