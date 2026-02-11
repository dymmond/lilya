import pytest

from lilya.testclient import TestClient
from lilya.testclient.async_client import AsyncTestClient

pytestmark = pytest.mark.anyio

def make_app():
    async def app(scope, receive, send):
        if scope["type"] == "http":
            user = scope.get("user", None)
            state = scope.get("state") or {}
            state_user = state.get("user", None)

            if user is None:
                payload = "none"
            else:
                payload = f"{id(user)}|{int(user is state_user)}"

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": payload.encode("utf-8")})
            return

        if scope["type"] == "websocket":
            await send({"type": "websocket.accept"})
            user = scope.get("user", None)
            state = scope.get("state") or {}
            state_user = state.get("user", None)

            if user is None:
                payload = "none"
            else:
                payload = f"{id(user)}|{int(user is state_user)}"

            await send({"type": "websocket.send", "text": payload})
            await send({"type": "websocket.close", "code": 1000})
            return

        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

    return app


def test_testclient_http_no_auth_user():
    app = make_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "none"


def test_testclient_http_authenticate_injects_user():
    app = make_app()
    user = object()
    client = TestClient(app).authenticate(user)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == f"{id(user)}|1"


def test_testclient_http_logout_clears_user():
    app = make_app()
    user = object()
    client = TestClient(app).authenticate(user).logout()
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "none"


def test_testclient_http_authenticated_context_restores_previous():
    app = make_app()
    user1 = object()
    user2 = object()
    client = TestClient(app).authenticate(user1)

    response1 = client.get("/")
    assert response1.text == f"{id(user1)}|1"

    with client.authenticated(user2):
        response2 = client.get("/")
        assert response2.text == f"{id(user2)}|1"

    response3 = client.get("/")
    assert response3.text == f"{id(user1)}|1"


def test_testclient_websocket_no_auth_user_scope():
    app = make_app()
    client = TestClient(app)
    session = client.websocket_connect("/ws")
    assert "user" not in session.scope


def test_testclient_websocket_authenticate_injects_user_scope():
    app = make_app()
    user = object()
    client = TestClient(app).authenticate(user)
    session = client.websocket_connect("/ws")
    assert session.scope["user"] is user
    assert session.scope["state"]["user"] is user


async def test_asynctestclient_http_no_auth_user():
    app = make_app()
    async with AsyncTestClient(app) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.text == "none"


async def test_asynctestclient_http_authenticate_injects_user():
    app = make_app()
    user = object()
    async with AsyncTestClient(app).authenticate(user) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.text == f"{id(user)}|1"


async def test_asynctestclient_http_logout_clears_user():
    app = make_app()
    user = object()
    async with AsyncTestClient(app).authenticate(user).logout() as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.text == "none"


async def test_asynctestclient_http_authenticated_context_restores_previous():
    app = make_app()
    user1 = object()
    user2 = object()

    async with AsyncTestClient(app).authenticate(user1) as client:
        response1 = await client.get("/")
        assert response1.text == f"{id(user1)}|1"

        with client.authenticated(user2):
            response2 = await client.get("/")
            assert response2.text == f"{id(user2)}|1"

        response3 = await client.get("/")
        assert response3.text == f"{id(user1)}|1"


async def test_asynctestclient_websocket_no_auth_user_scope():
    app = make_app()
    async with AsyncTestClient(app) as client:
        session = await client.websocket_connect("/ws")
        assert "user" not in session.scope


async def test_asynctestclient_websocket_authenticate_injects_user_scope():
    app = make_app()
    user = object()
    async with AsyncTestClient(app).authenticate(user) as client:
        session = await client.websocket_connect("/ws")
        assert session.scope["user"] is user
        assert session.scope["state"]["user"] is user
