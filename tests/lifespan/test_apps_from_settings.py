from contextlib import asynccontextmanager

import anyio
import pytest

from lilya import status
from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.controllers import Controller
from lilya.exceptions import HTTPException, ImproperlyConfigured, WebSocketException
from lilya.middleware.base import Middleware
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.responses import JSONResponse, PlainText
from lilya.routing import Host, Include, Path, Router, WebSocketPath
from lilya.types import ApplicationType
from lilya.websockets import WebSocket


async def error_500(request, exc):
    return JSONResponse({"detail": "Server Error"}, status_code=500)


async def method_not_allowed(request, exc):
    return JSONResponse({"detail": "Custom message"}, status_code=405)


async def http_exception(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def func_homepage():
    return PlainText("Hello, world!")


async def async_homepage():
    return PlainText("Hello, world!")


class Homepage(Controller):
    def get(self):
        return PlainText("Hello, world!")


def all_users_page():
    return PlainText("Hello, everyone!")


def user_page(request):
    username = request.path_params["username"]
    return PlainText(f"Hello, {username}!")


def custom_subdomain(request):
    return PlainText("Subdomain: " + request.path_params["subdomain"])


def runtime_error():
    raise RuntimeError()


async def websocket_handler(session):
    await session.accept()
    await session.send_text("Hello, world!")
    await session.close()


async def websocket_raise_websocket(websocket: WebSocket):
    await websocket.accept()
    raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA)


class CustomWSException(Exception):
    pass


async def websocket_raise_custom(websocket: WebSocket):
    await websocket.accept()
    raise CustomWSException()


def custom_ws_exception_handler(websocket: WebSocket, exc: CustomWSException):
    anyio.from_thread.run(websocket.close, status.WS_1013_TRY_AGAIN_LATER)


users = Router(
    routes=[
        Path("/", handler=all_users_page),
        Path("/{username}", handler=user_page),
    ]
)

subdomain = Router(
    routes=[
        Path("/", custom_subdomain),
    ]
)

exception_handlers = {
    500: error_500,
    405: method_not_allowed,
    HTTPException: http_exception,
    CustomWSException: custom_ws_exception_handler,
}

middleware = [Middleware(TrustedHostMiddleware, allowed_hosts=["testserver", "*.example.org"])]

app = Lilya(
    routes=[
        Path("/func", handler=func_homepage),
        Path("/async", handler=async_homepage),
        Path("/class", handler=Homepage),
        Path("/500", handler=runtime_error),
        WebSocketPath("/ws", handler=websocket_handler),
        WebSocketPath("/ws-raise-websocket", handler=websocket_raise_websocket),
        WebSocketPath("/ws-raise-custom", handler=websocket_raise_custom),
        Include("/users", app=users),
        Host("{subdomain}.example.org", app=subdomain),
    ],
    exception_handlers=exception_handlers,
    middleware=middleware,
)


def test_app_add_event_handler(test_client_factory):
    startup_complete = False
    cleanup_complete = False

    class MySettings(Settings):
        def on_startup(self):
            nonlocal startup_complete
            startup_complete = True

        def on_shutdown(self):
            nonlocal cleanup_complete
            cleanup_complete = True

    app = Lilya(
        settings_module=MySettings,
    )

    assert not startup_complete
    assert not cleanup_complete

    with test_client_factory(app):
        assert startup_complete
        assert not cleanup_complete

    assert startup_complete
    assert cleanup_complete


def test_app_async_cm_lifespan(test_client_factory):
    startup_complete = False
    cleanup_complete = False

    @asynccontextmanager
    async def _lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    class MySettings(Settings):
        def lifespan(self) -> ApplicationType | None:
            return _lifespan

    app = Lilya(settings_module=MySettings)

    assert not startup_complete
    assert not cleanup_complete
    with test_client_factory(app):
        assert startup_complete
        assert not cleanup_complete
    assert startup_complete
    assert cleanup_complete


def test_app_async_gen_lifespan(test_client_factory):
    startup_complete = False
    cleanup_complete = False

    @asynccontextmanager
    async def _lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    class MySettings(Settings):
        @property
        def lifespan(self) -> ApplicationType | None:
            return _lifespan

    app = Lilya(settings_module=MySettings)

    assert not startup_complete
    assert not cleanup_complete
    with test_client_factory(app):
        assert startup_complete
        assert not cleanup_complete
    assert startup_complete
    assert cleanup_complete


def test_app_sync_gen_lifespan(test_client_factory):
    startup_complete = False
    cleanup_complete = False

    def _lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    class MySettings(Settings):
        @property
        def lifespan(self) -> ApplicationType | None:
            return _lifespan

    with pytest.raises(ImproperlyConfigured):
        Lilya(settings_module=MySettings)
