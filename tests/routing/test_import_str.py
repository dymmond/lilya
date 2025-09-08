from lilya.apps import Lilya
from lilya.responses import Response
from lilya.routing import Path, WebSocketPath
from lilya.testclient import TestClient


def homepage():
    return Response("Hello, world", media_type="text/plain")


def users():
    return Response("All users", media_type="text/plain")


def test_import_str(test_client_factory):
    app = Lilya(
        routes=[
            Path("/", "tests.routing.test_import_str.homepage"),
            Path("/users", handler="tests.routing.test_import_str.users"),
        ]
    )

    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world"

    response = client.get("/users")
    assert response.status_code == 200
    assert response.text == "All users"


async def websocket_handler(session):
    await session.accept()
    await session.send_text("Hello, world!")
    await session.close()


def test_import_str_websocket(test_client_factory):
    app = Lilya(
        routes=[
            WebSocketPath("/ws", "tests.routing.test_import_str.websocket_handler"),
        ]
    )

    client = test_client_factory(app)

    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, world!"
