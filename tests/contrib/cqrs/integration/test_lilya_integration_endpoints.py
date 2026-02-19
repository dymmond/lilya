from __future__ import annotations

from lilya.apps import Lilya
from lilya.contrib.cqrs import CommandBus, QueryBus
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import RoutePath
from lilya.testclient import TestClient


class CreateUser:
    def __init__(self, user_id: str, email: str) -> None:
        self.user_id = user_id
        self.email = email


class GetUserEmail:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


def build_app():
    store: dict[str, str] = {}

    cmd_bus = CommandBus()
    qry_bus: QueryBus[str | None] = QueryBus()

    def handle_create(cmd: CreateUser) -> None:
        store[cmd.user_id] = cmd.email

    def handle_get(q: GetUserEmail) -> str | None:
        return store.get(q.user_id)

    cmd_bus.register(CreateUser, handle_create)
    qry_bus.register(GetUserEmail, handle_get)

    async def create_user(request: Request):
        data = await request.json()
        await cmd_bus.dispatch(CreateUser(user_id=data["user_id"], email=data["email"]))
        return JSONResponse({"status": "created"}, status_code=201)

    async def get_user_email(request: Request):
        user_id = request.path_params["user_id"]
        email = await qry_bus.ask(GetUserEmail(user_id=user_id))

        if email is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return JSONResponse({"user_id": user_id, "email": email})

    routes = [
        RoutePath("/users", create_user, methods=["POST"]),
        RoutePath("/users/{user_id}", get_user_email, methods=["GET"]),
    ]

    return Lilya(routes=routes)


def test_post_then_get_roundtrip(test_client_factory) -> None:
    app = build_app()
    client = TestClient(app)

    r = client.post("/users", json={"user_id": "u1", "email": "u1@example.com"})
    assert r.status_code == 201
    assert r.json() == {"status": "created"}

    r = client.get("/users/u1")
    assert r.status_code == 200
    assert r.json() == {"user_id": "u1", "email": "u1@example.com"}


def test_get_missing_returns_404(test_client_factory) -> None:
    app = build_app()
    client = TestClient(app)

    r = client.get("/users/nope")
    assert r.status_code == 404
    assert r.json() == {"detail": "not found"}


def test_post_invalid_json_is_error(test_client_factory) -> None:
    """
    We don't pin the exact error body because frameworks vary,
    but we prove Lilya is parsing request.json() and failing properly.
    """
    app = build_app()
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/users", content=b'{"user_id": "u2", "email": ')  # invalid JSON
    assert r.status_code >= 400
