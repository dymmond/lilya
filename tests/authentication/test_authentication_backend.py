from __future__ import annotations

import base64
import binascii
from collections.abc import Awaitable
from typing import Any, Callable
from urllib.parse import urlencode

import pytest

from lilya.apps import Lilya
from lilya.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BasicUser,
    requires,
)
from lilya.controllers import Controller
from lilya.middleware import DefineMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.requests import Connection, Request
from lilya.responses import JSONResponse, Response
from lilya.routing import Path, WebSocketPath
from lilya.websockets import WebSocket

AsyncEndpoint = Callable[..., Awaitable[Response]]
SyncEndpoint = Callable[..., Response]


class BasicAuth(AuthenticationBackend):
    async def authenticate(
        self,
        request: Connection,
    ) -> tuple[AuthCredentials, BasicUser] | None:
        if "Authorization" not in request.headers:
            return None

        auth = request.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise AuthenticationError("Invalid basic auth credentials") from None

        username, _, password = decoded.partition(":")
        return AuthCredentials(["authenticated"]), BasicUser(username)


def homepage(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


@requires("authenticated")
async def dashboard(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


@requires("authenticated", redirect="homepage")
async def admin(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


@requires("authenticated")
def dashboard_sync(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


class Dashboard(Controller):
    @requires("authenticated")
    def get(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "authenticated": request.user.is_authenticated,
                "user": request.user.display_name,
            }
        )


@requires("authenticated", redirect="homepage")
def admin_sync(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


@requires("authenticated")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "authenticated": websocket.user.is_authenticated,
            "user": websocket.user.display_name,
        }
    )


def async_inject_decorator(
    **kwargs: Any,
) -> Callable[[AsyncEndpoint], Callable[..., Awaitable[Response]]]:
    def wrapper(endpoint: AsyncEndpoint) -> Callable[..., Awaitable[Response]]:
        async def app(request: Request) -> Response:
            return await endpoint(request=request, **kwargs)

        return app

    return wrapper


@async_inject_decorator(additional="payload")
@requires("authenticated")
async def decorated_async(request: Request, additional: str) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
            "additional": additional,
        }
    )


def sync_inject_decorator(
    **kwargs: Any,
) -> Callable[[SyncEndpoint], Callable[..., Response]]:
    def wrapper(endpoint: SyncEndpoint) -> Callable[..., Response]:
        def app(request: Request) -> Response:
            return endpoint(request=request, **kwargs)

        return app

    return wrapper


@sync_inject_decorator(additional="payload")
@requires("authenticated")
def decorated_sync(request: Request, additional: str) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
            "additional": additional,
        }
    )


def ws_inject_decorator(**kwargs: Any) -> Callable[..., AsyncEndpoint]:
    def wrapper(endpoint: AsyncEndpoint) -> AsyncEndpoint:
        def app(websocket: WebSocket) -> Awaitable[Response]:
            return endpoint(websocket=websocket, **kwargs)

        return app

    return wrapper


@ws_inject_decorator(additional="payload")
@requires("authenticated")
async def websocket_endpoint_decorated(websocket: WebSocket, additional: str) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "authenticated": websocket.user.is_authenticated,
            "user": websocket.user.display_name,
            "additional": additional,
        }
    )


app = Lilya(
    middleware=[DefineMiddleware(AuthenticationMiddleware, backend=BasicAuth())],
    routes=[
        Path("/", handler=homepage),
        Path("/dashboard", handler=dashboard),
        Path("/admin", handler=admin),
        Path("/dashboard/sync", handler=dashboard_sync),
        Path("/dashboard/class", handler=Dashboard),
        Path("/admin/sync", handler=admin_sync),
        Path("/dashboard/decorated", handler=decorated_async),
        Path("/dashboard/decorated/sync", handler=decorated_sync),
        WebSocketPath("/ws", handler=websocket_endpoint),
        WebSocketPath("/ws/decorated", handler=websocket_endpoint_decorated),
    ],
)


def test_invalid_decorator_usage() -> None:
    with pytest.raises(Exception):  # noqa

        @requires("authenticated")
        def foo() -> None: ...


def test_user_interface(test_client_factory) -> None:
    with test_client_factory(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False, "user": ""}

        response = client.get("/", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}


def test_authentication_required(test_client_factory) -> None:
    with test_client_factory(app) as client:
        response = client.get("/dashboard")
        assert response.status_code == 403

        response = client.get("/dashboard", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}

        response = client.get("/dashboard/sync")
        assert response.status_code == 403

        response = client.get("/dashboard/sync", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}

        response = client.get("/dashboard/class")
        assert response.status_code == 403

        response = client.get("/dashboard/class", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}

        response = client.get("/dashboard/decorated", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {
            "authenticated": True,
            "user": "lilya",
            "additional": "payload",
        }

        response = client.get("/dashboard/decorated")
        assert response.status_code == 403

        response = client.get("/dashboard/decorated/sync", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {
            "authenticated": True,
            "user": "lilya",
            "additional": "payload",
        }

        response = client.get("/dashboard/decorated/sync")
        assert response.status_code == 403

        response = client.get("/dashboard", headers={"Authorization": "basic foobar"})
        assert response.status_code == 400
        assert response.text == "Invalid basic auth credentials"


def test_authentication_redirect(test_client_factory) -> None:
    with test_client_factory(app) as client:
        response = client.get("/admin")
        assert response.status_code == 200
        url = "{}?{}".format("http://testserver/", urlencode({"next": "http://testserver/admin"}))
        assert response.url == url

        response = client.get("/admin", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}

        response = client.get("/admin/sync")
        assert response.status_code == 200
        url = "{}?{}".format(
            "http://testserver/", urlencode({"next": "http://testserver/admin/sync"})
        )
        assert response.url == url

        response = client.get("/admin/sync", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}


def on_auth_error(request: Connection, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse({"error": str(exc)}, status_code=401)


@requires("authenticated")
def control_panel(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.display_name,
        }
    )


other_app = Lilya(
    routes=[Path("/control-panel", handler=control_panel)],
    middleware=[
        DefineMiddleware(
            AuthenticationMiddleware, backend=[BasicAuth(), BasicAuth()], on_error=on_auth_error
        )
    ],
)


def test_custom_on_error(test_client_factory) -> None:
    with test_client_factory(other_app) as client:
        response = client.get("/control-panel", auth=("lilya", "example"))
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": "lilya"}

        response = client.get("/control-panel", headers={"Authorization": "basic foobar"})
        assert response.status_code == 401
        assert response.json() == {"error": "Invalid basic auth credentials"}
