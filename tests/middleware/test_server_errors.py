from collections.abc import Callable
from typing import Any

import pytest

from lilya.apps import Lilya
from lilya.background import Task
from lilya.middleware.server_error import ServerErrorMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse, Response
from lilya.routing import Path
from lilya.testclient import TestClient
from lilya.types import Receive, Scope, Send

TestClientFactory = Callable[..., TestClient]


def test_handler(
    test_client_factory: TestClientFactory,
) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("Something went wrong")

    def error_500(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": "Server Error"}, status_code=500)

    app = ServerErrorMiddleware(app, handler=error_500)
    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 500
    assert response.json() == {"detail": "Server Error"}


def test_debug_text(test_client_factory: TestClientFactory) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("Something went wrong")

    app = ServerErrorMiddleware(app, debug=True)
    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("text/plain")
    assert "RuntimeError: Something went wrong" in response.text


def test_debug_html(test_client_factory: TestClientFactory) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("Something went wrong")

    app = ServerErrorMiddleware(app, debug=True)
    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Accept": "text/html, */*"})
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("text/html")
    assert "RuntimeError" in response.text


def test_debug_after_response_sent(test_client_factory: TestClientFactory) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        response = Response(b"", status_code=204)
        await response(scope, receive, send)
        raise RuntimeError("Something went wrong")

    app = ServerErrorMiddleware(app, debug=True)
    client = test_client_factory(app)
    with pytest.raises(RuntimeError):
        client.get("/")


def test_debug_not_http(test_client_factory: TestClientFactory) -> None:
    """
    DebugMiddleware should just pass through any non-http messages as-is.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("Something went wrong")

    app = ServerErrorMiddleware(app)

    with pytest.raises(RuntimeError):
        client = test_client_factory(app)
        with client.websocket_connect("/"):
            pass  # pragma: nocover


def test_background_task(test_client_factory: TestClientFactory) -> None:
    accessed_error_handler = False

    def error_handler(request: Request, exc: Exception) -> Any:
        nonlocal accessed_error_handler
        accessed_error_handler = True

    def raise_exception() -> None:
        raise Exception("Something went wrong")

    async def endpoint() -> Response:
        task = Task(raise_exception)
        return Response(status_code=204, background=task)

    app = Lilya(
        routes=[Path("/", handler=endpoint)],
        exception_handlers={Exception: error_handler},
    )

    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 204
    assert accessed_error_handler
