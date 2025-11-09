from collections.abc import Callable, Iterator

import pytest

from lilya.controllers import Controller, WebSocketController
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.routing import Path, Router
from lilya.testclient import TestClient
from lilya.websockets import WebSocket

TestClientFactory = Callable[..., TestClient]


class Homepage(Controller):
    async def get(self, request: Request) -> PlainText:
        username = request.path_params.get("username")
        if username is None:
            return PlainText("Hello, world!")
        return PlainText(f"Hello, {username}!")

    async def post(self) -> PlainText:
        return PlainText("Hello world, no request needed!")


app = Router(routes=[Path("/", handler=Homepage), Path("/{username}", handler=Homepage)])


@pytest.fixture
def client(test_client_factory: TestClientFactory) -> Iterator[TestClient]:
    with test_client_factory(app) as client:
        yield client


def test_add_route(test_client_factory: TestClientFactory) -> None:
    class TestController(Controller):
        async def get(self) -> PlainText:
            return PlainText("Hello, world!")

    app = Router()
    app.add_route("/", TestController)
    client = test_client_factory(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_http_endpoint_route(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world!"

    response = client.post("/")
    assert response.status_code == 200
    assert response.text == "Hello world, no request needed!"


def test_http_endpoint_route_path_params(client: TestClient) -> None:
    response = client.get("/lilya")
    assert response.status_code == 200
    assert response.text == "Hello, lilya!"


def test_http_endpoint_route_method(client: TestClient) -> None:
    response = client.put("/")
    assert response.status_code == 405
    assert response.text == "Method Not Allowed"
    assert response.headers["allow"] == "GET, POST"


def test_websocket_endpoint_on_connect(test_client_factory: TestClientFactory) -> None:
    class WebSocketApp(WebSocketController):
        async def on_connect(self, websocket: WebSocket) -> None:
            assert websocket["subprotocols"] == ["soap", "wamp"]
            await websocket.accept(subprotocol="wamp")

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws", subprotocols=["soap", "wamp"]) as websocket:
        assert websocket.accepted_subprotocol == "wamp"


def test_websocket_endpoint_on_receive_bytes(
    test_client_factory: TestClientFactory,
) -> None:
    class WebSocketApp(WebSocketController):
        encoding = "bytes"

        async def on_receive(self, websocket: WebSocket, data: bytes) -> None:
            await websocket.send_bytes(b"Message bytes was: " + data)

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_bytes(b"Hello, world!")
        _bytes = websocket.receive_bytes()
        assert _bytes == b"Message bytes was: Hello, world!"

    with pytest.raises(RuntimeError):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Hello world")


def test_websocket_endpoint_on_receive_json(
    test_client_factory: TestClientFactory,
) -> None:
    class WebSocketApp(WebSocketController):
        encoding = "json"

        async def on_receive(self, websocket: WebSocket, data: str) -> None:
            await websocket.send_json({"message": data})

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"hello": "world"})
        data = websocket.receive_json()
        assert data == {"message": {"hello": "world"}}

    with pytest.raises(RuntimeError):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Hello world")


def test_websocket_endpoint_on_receive_json_binary(
    test_client_factory: TestClientFactory,
) -> None:
    class WebSocketApp(WebSocketController):
        encoding = "json"

        async def on_receive(self, websocket: WebSocket, data: str) -> None:
            await websocket.send_json({"message": data}, mode="binary")

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"hello": "world"}, mode="binary")
        data = websocket.receive_json(mode="binary")
        assert data == {"message": {"hello": "world"}}


def test_websocket_endpoint_on_receive_text(
    test_client_factory: TestClientFactory,
) -> None:
    class WebSocketApp(WebSocketController):
        encoding = "text"

        async def on_receive(self, websocket: WebSocket, data: str) -> None:
            await websocket.send_text(f"Message text was: {data}")

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, world!")
        _text = websocket.receive_text()
        assert _text == "Message text was: Hello, world!"

    with pytest.raises(RuntimeError):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_bytes(b"Hello world")


def test_websocket_endpoint_on_default(test_client_factory: TestClientFactory) -> None:
    class WebSocketApp(WebSocketController):
        encoding = None

        async def on_receive(self, websocket: WebSocket, data: str) -> None:
            await websocket.send_text(f"Message text was: {data}")

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, world!")
        _text = websocket.receive_text()
        assert _text == "Message text was: Hello, world!"


def test_websocket_endpoint_on_disconnect(
    test_client_factory: TestClientFactory,
) -> None:
    class WebSocketApp(WebSocketController):
        async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
            assert close_code == 1001
            await websocket.close(code=close_code)

    client = test_client_factory(WebSocketApp)
    with client.websocket_connect("/ws") as websocket:
        websocket.close(code=1001)


def test_http_with_init_instantiation_and_response(
    test_client_factory: Callable[..., TestClient],
) -> None:
    class Greeter(Controller):
        def __init__(self, *, greeting: str, punct: str = "!") -> None:
            self.greeting = greeting
            self.punct = punct

        async def get(self, request: Request) -> PlainText:
            name = request.query_params.get("name", "world")
            return PlainText(f"{self.greeting}, {name}{self.punct}")

    app = Router(
        routes=[
            Path("/", handler=Greeter.with_init(greeting="Hello", punct="!!!")),
        ]
    )
    client = test_client_factory(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world!!!"

    response = client.get("/?name=Lilya")
    assert response.status_code == 200
    assert response.text == "Hello, Lilya!!!"


def test_http_with_init_allows_router_zero_arg_init() -> None:
    class NeedArgs(Controller):
        def __init__(self, value: int) -> None:
            self.value = value

        async def get(self) -> PlainText:
            return PlainText(str(self.value))

    # Router must be able to do `self.app()` with no args
    Wrapped = NeedArgs.with_init(42)

    # Emulate router, calling the returned class with no args should not crash
    instance = Wrapped()

    assert isinstance(instance, Controller)


def test_http_with_init_wrapper_is_singleton() -> None:
    class C(Controller):
        def __init__(self, x: int) -> None:
            self.x = x

        async def get(self) -> PlainText:
            return PlainText(str(self.x))

    Wrapped = C.with_init(10)

    a = Wrapped()
    b = Wrapped()

    assert a is b


def test_http_with_init_per_request_controller_created(
    test_client_factory: Callable[..., TestClient],
) -> None:
    class Counter(Controller):
        created = 0  # class-level counter to observe per-request instantiation

        def __init__(self, *, seed: int) -> None:
            type(self).created += 1
            self.seed = seed

        async def get(self) -> PlainText:
            return PlainText(str(self.seed))

    app = Router(routes=[Path("/", handler=Counter.with_init(seed=7))])
    client = test_client_factory(app)

    assert Counter.created == 0

    r1 = client.get("/")
    r2 = client.get("/")

    assert r1.text == "7"
    assert r2.text == "7"

    # Two requests: two real controller instances
    assert Counter.created == 2


def test_http_with_init_method_not_allowed(test_client_factory: Callable[..., TestClient]) -> None:
    class OnlyGet(Controller):
        def __init__(self, msg: str) -> None:
            self.msg = msg

        async def get(self) -> PlainText:
            return PlainText(self.msg)

    app = Router(routes=[Path("/", handler=OnlyGet.with_init("ok"))])
    client = test_client_factory(app)

    resp = client.put("/")

    assert resp.status_code == 405
    assert resp.text == "Method Not Allowed"

    # allow header reflects methods on the *real* controller
    assert resp.headers["allow"] == "GET"


def test_websocket_with_init_basic_echo(test_client_factory: TestClientFactory) -> None:
    class EchoWS(WebSocketController):
        def __init__(self, scope, receive, send, *, prefix: str) -> None:
            super().__init__(scope, receive, send)
            self.prefix = prefix
            self.encoding = "text"

        async def on_receive(self, websocket: WebSocket, data: str) -> None:
            await websocket.send_text(f"{self.prefix}:{data}")

    client = test_client_factory(EchoWS.with_init(prefix="hi"))
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")

        assert ws.receive_text() == "hi:ping"


def test_websocket_with_init_router_zero_arg_init() -> None:
    class NeedArgsWS(WebSocketController):
        def __init__(self, scope, receive, send, token: str) -> None:
            super().__init__(scope, receive, send)
            self.token = token

        async def on_receive(self, websocket: WebSocket, data: str) -> None: ...

    Wrapped = NeedArgsWS.with_init("secret")
    instance = Wrapped()

    assert isinstance(instance, WebSocketController)


def test_websocket_with_init_wrapper_singleton() -> None:
    class W(WebSocketController):
        def __init__(self, scope, receive, send, x: int) -> None:
            super().__init__(scope, receive, send)
            self.x = x

    Wrapped = W.with_init(1)
    a = Wrapped()
    b = Wrapped()

    assert a is b


def test_websocket_with_init_json_roundtrip(test_client_factory: TestClientFactory) -> None:
    class JsonWS(WebSocketController):
        def __init__(self, scope, receive, send, *, tag: str) -> None:
            super().__init__(scope, receive, send)
            self.tag = tag
            self.encoding = "json"

        async def on_receive(self, websocket: WebSocket, data) -> None:
            await websocket.send_json({"tag": self.tag, "data": data})

    client = test_client_factory(JsonWS.with_init(tag="T"))
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"hello": "world"})

        assert ws.receive_json() == {"tag": "T", "data": {"hello": "world"}}
