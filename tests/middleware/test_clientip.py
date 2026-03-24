from collections.abc import Callable

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPMiddleware, ClientIPScopeOnlyMiddleware
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import TestClient
from lilya.types import ASGIApp, Receive, Scope, Send

TestClientFactory = Callable[..., TestClient]


class InjectClientIPMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, *, client: tuple[str, int]) -> None:
        self.app = app
        self.client = client

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["client"] = self.client
        await self.app(scope, receive, send)


class InjectIPMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, *, ip: str) -> None:
        self.app = app
        self.ip = ip

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope[ClientIPMiddleware.scope_name] = self.ip
        await self.app(scope, receive, send)


def test_clientip_none(test_client_factory: TestClientFactory):
    def homepage(request: Request):
        assert request.headers.get("x-real-ip") == "127.0.0.1"
        assert request.scope.get("real-clientip") == "127.0.0.1"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(InjectClientIPMiddleware, client=("127.0.0.1", 3882)),
            DefineMiddleware(ClientIPMiddleware, trusted_proxies=[]),
        ],
    )

    client = test_client_factory(app)
    client.get("/")
    client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})


def test_clientip_none_sanitize(test_client_factory: TestClientFactory):
    def homepage(request: Request):
        assert request.headers.get("x-real-ip") == "::ffff:17.0.0.1"
        assert request.scope.get("real-clientip") == "::ffff:17.0.0.1"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(InjectClientIPMiddleware, client=("::ffff:17.0.0.1", 77)),
            DefineMiddleware(
                ClientIPMiddleware,
                trusted_proxies=[],
                sanitize_proxyip=lambda x: x.removeprefix("::ffff:"),
            ),
        ],
    )

    client = test_client_factory(app)
    client.get("/")
    client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})


def test_clientip_proxy_sanitize(test_client_factory: TestClientFactory):
    def homepage(request: Request):
        assert request.headers.get("x-real-ip") == "8.193.38.177"
        assert request.scope.get("real-clientip") == "8.193.38.177"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(InjectClientIPMiddleware, client=("::ffff:17.0.0.1", 77)),
            DefineMiddleware(
                ClientIPMiddleware,
                trusted_proxies=["17.0.0.1"],
                sanitize_proxyip=lambda x: x.removeprefix("::ffff:"),
                sanitize_clientip=lambda x: x.removeprefix("::ffff:"),
            ),
        ],
    )

    client = test_client_factory(app)
    client.get("/", headers={"forwarded": "for=::ffff:8.193.38.177,for=8.193.38.176"})


def test_clientip_all(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
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
    def homepage(request: Request) -> PlainText:
        assert request.scope.get("real-clientip") == "8.193.38.177"
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
    def homepage(request: Request) -> PlainText:
        assert request.scope.get("real-clientip") == "8.193.38.177"
        assert not request.headers.get("x-real-ip")
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=["unix"])],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})
    assert response.status_code == 200


def test_clientip_ip_scope_overwrite_existing(test_client_factory: TestClientFactory) -> None:
    def homepage(request: Request) -> PlainText:
        assert request.scope.get("real-clientip") == "8.193.38.177"
        assert request.headers.get("x-real-ip") == "8.193.38.177"
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[
            DefineMiddleware(InjectIPMiddleware, ip="8.194.2.188"),
            DefineMiddleware(
                ClientIPMiddleware,
                trusted_proxies=["unix"],
            ),
        ],
    )

    client = test_client_factory(app)
    response = client.get("/", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"})
    assert response.status_code == 200
