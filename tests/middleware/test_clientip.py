from collections.abc import Callable

import pytest

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPMiddleware, ClientIPScopeOnlyMiddleware
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import TestClient

TestClientFactory = Callable[..., TestClient]


@pytest.mark.xfail(reason="Setting a simulated client ip is not supported.")
def test_clientip_none(test_client_factory: TestClientFactory):
    def homepage(request: Request):
        assert request.headers.get("x-real-ip") == "127.0.0.1"
        assert request.scope.get("real-clientip") == "127.0.0.1"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(ClientIPMiddleware, trusted_proxies=[])],
    )

    client = test_client_factory(app)
    client.get("/")
    client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})


def test_clientip_all(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> None:
        assert request.headers.get("x-real-ip") == "8.193.38.177"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(ClientIPMiddleware, trusted_proxies=["*"])],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})
    assert response.status_code == 200


def test_clientip_ip(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> None:
        assert request.headers.get("x-real-ip") == "8.193.38.177"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(ClientIPMiddleware, trusted_proxies=["unix"])],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})
    assert response.status_code == 200


def test_clientip_ip_scope_only(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> None:
        assert request.scope.get("real-clientip") == "8.193.38.177"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=["unix"])],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})
    assert response.status_code == 200
