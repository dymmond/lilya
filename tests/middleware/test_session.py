import re
from typing import Callable

from lilya.app import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Include, Path
from lilya.testclient import TestClient

TestClientFactory = Callable[..., TestClient]


def view_session(request: Request) -> JSONResponse:
    return JSONResponse({"session": request.session})


async def update_session(request: Request) -> JSONResponse:
    data = await request.json()
    request.session.update(data)
    return JSONResponse({"session": request.session})


async def clear_session(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"session": request.session})


def test_session(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
            Path("/clear_session", handler=clear_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example")],
    )
    client = test_client_factory(app)

    response = client.get("/view_session")
    assert response.json() == {"session": {}}

    response = client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    # check cookie max-age
    set_cookie = response.headers["set-cookie"]
    max_age_matches = re.search(r"; Max-Age=([0-9]+);", set_cookie)
    assert max_age_matches is not None
    assert int(max_age_matches[1]) == 14 * 24 * 3600

    response = client.get("/view_session")
    assert response.json() == {"session": {"some": "data"}}

    response = client.post("/clear_session")
    assert response.json() == {"session": {}}

    response = client.get("/view_session")
    assert response.json() == {"session": {}}


def test_session_expires(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example", max_age=-1)],
    )
    client = test_client_factory(app)

    response = client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    expired_cookie_header = response.headers["set-cookie"]
    expired_session_match = re.search(r"session=([^;]*);", expired_cookie_header)

    assert expired_session_match is not None

    expired_session_value = expired_session_match[1]
    client = test_client_factory(app, cookies={"session": expired_session_value})
    response = client.get("/view_session")

    assert response.json() == {"session": {}}


def test_secure_session(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
            Path("/clear_session", handler=clear_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example", https_only=True)],
    )
    secure_client = test_client_factory(app, base_url="https://testserver")
    unsecure_client = test_client_factory(app, base_url="http://testserver")

    response = unsecure_client.get("/view_session")
    assert response.json() == {"session": {}}

    response = unsecure_client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    response = unsecure_client.get("/view_session")
    assert response.json() == {"session": {}}

    response = secure_client.get("/view_session")
    assert response.json() == {"session": {}}

    response = secure_client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    response = secure_client.get("/view_session")
    assert response.json() == {"session": {"some": "data"}}

    response = secure_client.post("/clear_session")
    assert response.json() == {"session": {}}

    response = secure_client.get("/view_session")
    assert response.json() == {"session": {}}


def test_session_cookie_subpath(test_client_factory: TestClientFactory) -> None:
    second_app = Lilya(
        routes=[
            Path("/update_session", handler=update_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example", path="/second_app")],
    )

    app = Lilya(routes=[Include("/second_app", app=second_app)])
    client = test_client_factory(app, base_url="http://testserver/second_app")

    response = client.post("/second_app/update_session", json={"some": "data"})
    assert response.status_code == 200

    cookie = response.headers["set-cookie"]
    cookie_path_match = re.search(r"; path=(\S+);", cookie)
    assert cookie_path_match is not None

    cookie_path = cookie_path_match.groups()[0]
    assert cookie_path == "/second_app"


def test_invalid_session_cookie(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example")],
    )
    client = test_client_factory(app)

    response = client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    client = test_client_factory(app, cookies={"session": "invalid"})
    response = client.get("/view_session")
    assert response.json() == {"session": {}}


def test_session_cookie(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
        ],
        middleware=[DefineMiddleware(SessionMiddleware, secret_key="example", max_age=None)],
    )
    client: TestClient = test_client_factory(app)

    response = client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    set_cookie = response.headers["set-cookie"]
    assert "Max-Age" not in set_cookie

    client.cookies.delete("session")
    response = client.get("/view_session")
    assert response.json() == {"session": {}}


def test_domain_cookie(test_client_factory: TestClientFactory) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
        ],
        middleware=[
            DefineMiddleware(SessionMiddleware, secret_key="example", domain=".example.com")
        ],
    )
    client: TestClient = test_client_factory(app)

    response = client.post("/update_session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    set_cookie = response.headers["set-cookie"]
    assert "domain=.example.com" in set_cookie

    client.cookies.delete("session")
    response = client.get("/view_session")
    assert response.json() == {"session": {}}
