from collections.abc import Iterator
from typing import Callable

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
