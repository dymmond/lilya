from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from lilya.responses import Response
from lilya.routing import Include, Path, Router, WebSocketPath
from lilya.testclient import TestClient
from lilya.websockets import WebSocket


def homepage():
    return Response("Hello, world", media_type="text/plain")


def users():
    return Response("All users", media_type="text/plain")


def user(request):
    content = "User " + request.path_params["username"]
    return Response(content, media_type="text/plain")


def user_me():
    content = "User fixed me"
    return Response(content, media_type="text/plain")


def user_me2():
    content = "User fixed me2"
    return Response(content, media_type="text/plain")


def user_me_post():
    content = "User fixed me_post"
    return Response(content, media_type="text/plain")


def disable_user(request):
    content = "User " + request.path_params["username"] + " disabled"
    return Response(content, media_type="text/plain")


def user_no_match():  # pragma: no cover
    content = "User fixed no match"
    return Response(content, media_type="text/plain")


async def websocket_handler(session: WebSocket):
    await session.accept()
    await session.send_text("Hello, world!")
    await session.close()


async def websocket_params(session: WebSocket):
    await session.accept()
    await session.send_text(f"Hello, {session.path_params['room']}!")
    await session.close()


path2 = Path("/me/", handler=user_me2)
# the default is stripping trailing /, so we readd this to the regex
path2.path_regex = re.compile("^/me/$")
app = Router(
    [
        Path("/", handler=homepage, methods=["GET"]),
        Include(
            "/",
            routes=[
                Path("/me", handler=user_me),
                Path("/me", handler=user_me_post, methods=["POST"]),
            ],
            redirect_slashes=False,
        ),
        Include(
            "/",
            routes=[
                path2,
                Path("/me2/", handler=user_me2),
            ],
        ),
        WebSocketPath("/me", handler=websocket_handler),
        WebSocketPath("/me/{room}", handler=websocket_params),
    ]
)


@pytest.fixture
def client(test_client_factory: Callable[..., TestClient]):
    with test_client_factory(app) as client:
        yield client


def test_router(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world"

    response = client.post("/")
    assert response.status_code == 405
    assert response.text == "Method Not Allowed"
    assert set(response.headers["allow"].split(", ")) == {"HEAD", "GET"}

    response = client.get("/foo")
    assert response.status_code == 404
    assert response.text == "Not Found"

    response = client.get("/me")
    assert response.status_code == 200
    assert response.text == "User fixed me"

    response = client.post("/me")
    assert response.status_code == 200
    assert response.text == "User fixed me_post"

    response = client.get("/me2")
    assert response.status_code == 200
    assert response.text == "User fixed me2"

    # check redirect_slashes is off
    response = client.get("/me/")
    assert response.status_code == 200
    assert response.text == "User fixed me2"


def test_router_add_websocket_path(client):
    with client.websocket_connect("/me") as session:
        text = session.receive_text()
        assert text == "Hello, world!"

    with client.websocket_connect("/me/test") as session:
        text = session.receive_text()
        assert text == "Hello, test!"
