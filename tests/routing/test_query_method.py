from __future__ import annotations

from collections.abc import Callable

from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.middleware import DefineMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse, PlainText
from lilya.routing import Path
from lilya.testclient import TestClient
from lilya.types import ASGIApp, Receive, Scope, Send


class CaptureMethodMiddleware:
    def __init__(self, app: ASGIApp, seen_methods: list[str]) -> None:
        self.app = app
        self.seen_methods = seen_methods

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            self.seen_methods.append(scope["method"])
        await self.app(scope, receive, send)


def test_query_route_without_body_and_reverse_lookup(
    test_client_factory: Callable[..., TestClient],
) -> None:
    async def search(request: Request) -> JSONResponse:
        body = await request.body()
        return JSONResponse({"method": request.method, "body": body.decode()})

    app = Lilya(routes=[Path("/search", search, methods=["QUERY"], name="search")])

    with test_client_factory(app) as client:
        response = client.query("/search")

    assert response.status_code == 200
    assert response.json() == {"method": "QUERY", "body": ""}
    assert str(app.url_path_for("search")) == "/search"


def test_query_route_with_json_body(
    test_client_factory: Callable[..., TestClient],
) -> None:
    async def search(request: Request) -> JSONResponse:
        return JSONResponse({"method": request.method, "json": await request.json()})

    app = Lilya(routes=[Path("/search", search, methods=["QUERY"])])

    with test_client_factory(app) as client:
        helper_response = client.query("/search", json={"filters": {"status": "active"}})
        generic_response = client.request("QUERY", "/search", json={"limit": 10})

    assert helper_response.status_code == 200
    assert helper_response.json() == {
        "method": "QUERY",
        "json": {"filters": {"status": "active"}},
    }
    assert generic_response.status_code == 200
    assert generic_response.json() == {"method": "QUERY", "json": {"limit": 10}}


def test_query_route_with_raw_body(
    test_client_factory: Callable[..., TestClient],
) -> None:
    async def search(request: Request) -> JSONResponse:
        body = await request.body()
        return JSONResponse({"method": request.method, "body": body.decode()})

    app = Lilya(routes=[Path("/search", search, methods=["QUERY"])])

    with test_client_factory(app) as client:
        text_response = client.query("/search", content="select=name&limit=10")
        bytes_response = client.query("/search", content=b"\x00query-bytes")

    assert text_response.status_code == 200
    assert text_response.json() == {"method": "QUERY", "body": "select=name&limit=10"}
    assert bytes_response.status_code == 200
    assert bytes_response.json() == {"method": "QUERY", "body": "\x00query-bytes"}


def test_query_method_matching_is_isolated(
    test_client_factory: Callable[..., TestClient],
) -> None:
    def query_search() -> PlainText:
        return PlainText("query")

    def create_search() -> PlainText:
        return PlainText("post")

    app = Lilya(
        routes=[
            Path("/search", query_search, methods=["QUERY"]),
            Path("/create", create_search, methods=["POST"]),
        ]
    )

    with test_client_factory(app) as client:
        get_response = client.get("/search")
        post_response = client.post("/search")
        query_to_post_response = client.query("/create")

    assert get_response.status_code == 405
    assert get_response.headers["allow"] == "QUERY"
    assert post_response.status_code == 405
    assert post_response.headers["allow"] == "QUERY"
    assert query_to_post_response.status_code == 405
    assert query_to_post_response.headers["allow"] == "POST"


def test_query_decorator_and_generic_route(
    test_client_factory: Callable[..., TestClient],
) -> None:
    app = Lilya()

    @app.query("/decorated")
    async def decorated() -> PlainText:
        return PlainText("decorated")

    @app.route("/generic", methods=["QUERY"])
    async def generic() -> PlainText:
        return PlainText("generic")

    with test_client_factory(app) as client:
        decorated_response = client.query("/decorated")
        generic_response = client.query("/generic")

    assert decorated_response.status_code == 200
    assert decorated_response.text == "decorated"
    assert generic_response.status_code == 200
    assert generic_response.text == "generic"


def test_query_controller_dispatch(
    test_client_factory: Callable[..., TestClient],
) -> None:
    class SearchController(Controller):
        async def query(self, request: Request) -> JSONResponse:
            return JSONResponse({"method": request.method, "json": await request.json()})

    app = Lilya(routes=[Path("/search", SearchController)])

    with test_client_factory(app) as client:
        response = client.query("/search", json={"filters": ["active"]})
        get_response = client.get("/search")

    assert response.status_code == 200
    assert response.json() == {"method": "QUERY", "json": {"filters": ["active"]}}
    assert get_response.status_code == 405


def test_query_method_reaches_middleware(
    test_client_factory: Callable[..., TestClient],
) -> None:
    seen_methods: list[str] = []

    def handler() -> PlainText:
        return PlainText("ok")

    app = Lilya(
        routes=[Path("/search", handler, methods=["QUERY"])],
        middleware=[DefineMiddleware(CaptureMethodMiddleware, seen_methods=seen_methods)],
    )

    with test_client_factory(app) as client:
        response = client.query("/search")

    assert response.status_code == 200
    assert seen_methods == ["QUERY"]
