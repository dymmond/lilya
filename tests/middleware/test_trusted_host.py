from collections.abc import Callable

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import TestClient

TestClientFactory = Callable[..., TestClient]


def test_trusted_host_middleware(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope["host_is_trusted"]
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["testserver", "*.testserver"])
        ],
    )

    client = test_client_factory(app)
    response = client.get("/")
    assert response.status_code == 200

    client = test_client_factory(app, base_url="http://subdomain.testserver")
    response = client.get("/")
    assert response.status_code == 200

    client = test_client_factory(app, base_url="http://invalidhost")
    response = client.get("/")
    assert response.status_code == 400


def test_trusted_host_middleware_scope_only(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        return PlainText(f"{request.scope['host_is_trusted']}", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(
                TrustedHostMiddleware,
                allowed_hosts=["testserver", "*.testserver"],
                block_untrusted_hosts=False,
            )
        ],
    )

    client = test_client_factory(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "True"

    client = test_client_factory(app, base_url="http://subdomain.testserver")
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "True"

    client = test_client_factory(app, base_url="http://invalidhost")
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "False"


def test_default_allowed_hosts() -> None:
    app = Lilya()
    middleware = TrustedHostMiddleware(app)
    assert middleware.allowed_hosts == {"*"}


def test_www_redirect(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        return PlainText("OK", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["www.example.com"])],
    )

    client = test_client_factory(app, base_url="https://example.com")
    response = client.get("/")
    assert response.status_code == 200
    assert response.url == "https://www.example.com/"
