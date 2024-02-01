from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path, WebSocketPath
from lilya.testclient import TestClient
from lilya.websockets import WebSocket


def home():
    return Ok(
        {"detail": "welcome home"},
    )


def home_with_request(request: Request):
    return Ok(request.path_params)


async def websocket_endpoint(session: WebSocket):
    await session.accept()
    await session.send_text("Hello, Lilya")
    await session.close()


def test_path(test_client_factory):
    path = Path(path="/test/{name}", handler=home)

    client = TestClient(path)
    response = client.get("test/lilya")

    assert response.status_code == 200
    assert response.json() == {"detail": "welcome home"}


def test_path_with_request(test_client_factory):
    path = Path(path="/test/{name}", handler=home_with_request)

    client = TestClient(path)
    response = client.get("test/lilya")

    assert response.status_code == 200
    assert response.json() == {"name": "lilya"}


def test_websocket_path(test_client_factory):
    websocket = WebSocketPath("/ws", handler=websocket_endpoint)

    client = TestClient(websocket)

    with client.websocket_connect("/ws") as session:
        text = session.receive_text()

        assert text == "Hello, Lilya"
