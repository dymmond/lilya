import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import anyio
import httpx
import pytest

from lilya import status
from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.exceptions import HTTPException, ImproperlyConfigured, WebSocketException
from lilya.middleware.asyncexit import AsyncExitStackMiddleware
from lilya.middleware.base import Middleware
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.responses import JSONResponse, PlainText
from lilya.routing import Host, Include, Path, Router, WebSocketPath
from lilya.staticfiles import StaticFiles
from lilya.types import ASGIApp, Receive, Scope, Send
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


@pytest.fixture
def client(test_client_factory):
    with test_client_factory(app) as client:
        yield client


def test_url_path_for():
    assert app.path_for("func_homepage") == "/func"


def test_func_route(client):
    response = client.get("/func")
    assert response.status_code == 200
    assert response.text == "Hello, world!"

    response = client.head("/func")
    assert response.status_code == 200
    assert response.text == ""


def test_async_route(client):
    response = client.get("/async")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_class_route(client):
    response = client.get("/class")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_mounted_route(client):
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.text == "Hello, everyone!"


def test_mounted_route_path_params(client):
    response = client.get("/users/lilya")
    assert response.status_code == 200
    assert response.text == "Hello, lilya!"


def test_subdomain_route(test_client_factory):
    client = test_client_factory(app, base_url="https://foo.example.org/")

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Subdomain: foo"


def test_websocket_route(client):
    with client.websocket_connect("/ws") as session:
        text = session.receive_text()
        assert text == "Hello, world!"


def test_400(client):
    response = client.get("/404")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_405(client):
    response = client.post("/func")
    assert response.status_code == 405
    assert response.json() == {"detail": "Custom message"}

    response = client.post("/class")
    assert response.status_code == 405
    assert response.json() == {"detail": "Custom message"}


def test_500(test_client_factory):
    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/500")
    assert response.status_code == 500
    assert response.json() == {"detail": "Server Error"}


def test_websocket_raise_websocket_exception(client):
    with client.websocket_connect("/ws-raise-websocket") as session:
        response = session.receive()
        assert response == {
            "type": "websocket.close",
            "code": status.WS_1003_UNSUPPORTED_DATA,
            "reason": "",
        }


def test_websocket_raise_custom_exception(client):
    with client.websocket_connect("/ws-raise-custom") as session:
        response = session.receive()
        assert response == {
            "type": "websocket.close",
            "code": status.WS_1013_TRY_AGAIN_LATER,
            "reason": "",
        }


def test_middleware(test_client_factory):
    client = test_client_factory(app, base_url="http://incorrecthost")
    response = client.get("/func")
    assert response.status_code == 400
    assert response.text == "Invalid host header"


def test_app_mount(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "example.html")
    with open(path, "w") as file:
        file.write("<file content>")

    app = Lilya(
        routes=[
            Include("/static", StaticFiles(directory=tmpdir)),
        ]
    )

    client = test_client_factory(app)

    response = client.get("/static/example.html")
    assert response.status_code == 200
    assert response.text == "<file content>"

    response = client.post("/static/example.html")
    assert response.status_code == 405
    assert response.text == "Method Not Allowed"


def test_app_debug(test_client_factory):
    async def homepage(request):
        raise RuntimeError()

    app = Lilya(
        routes=[
            Path("/", homepage),
        ],
        middleware=[AsyncExitStackMiddleware],
    )
    app.debug = True

    client = test_client_factory(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 500
    assert "RuntimeError" in response.text
    assert app.debug


def test_app_add_route(test_client_factory):
    async def homepage(request):
        return PlainText("Hello, World!")

    app = Lilya(
        routes=[
            Path("/", handler=homepage),
        ]
    )

    client = test_client_factory(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_app_add_websocket_route(test_client_factory):
    async def websocket_handler(session):
        await session.accept()
        await session.send_text("Hello, world!")
        await session.close()

    app = Lilya(
        routes=[
            WebSocketPath("/ws", handler=websocket_handler),
        ]
    )
    client = test_client_factory(app)

    with client.websocket_connect("/ws") as session:
        text = session.receive_text()
        assert text == "Hello, world!"


def test_app_add_event_handler(test_client_factory):
    startup_complete = False
    cleanup_complete = False

    def run_startup():
        nonlocal startup_complete
        startup_complete = True

    def run_cleanup():
        nonlocal cleanup_complete
        cleanup_complete = True

    app = Lilya(
        on_startup=[run_startup],
        on_shutdown=[run_cleanup],
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
    async def lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    app = Lilya(lifespan=lifespan)

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
    async def lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    app = Lilya(lifespan=lifespan)

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

    def lifespan(app):
        nonlocal startup_complete, cleanup_complete
        startup_complete = True
        yield
        cleanup_complete = True

    with pytest.raises(ImproperlyConfigured):
        Lilya(lifespan=lifespan)


def test_middleware_stack_init(test_client_factory: Callable[[ASGIApp], httpx.Client]):
    class NoOpMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await self.app(scope, receive, send)

    class SimpleInitializableMiddleware:
        counter = 0

        def __init__(self, app: ASGIApp):
            self.app = app
            SimpleInitializableMiddleware.counter += 1

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await self.app(scope, receive, send)

    def get_app() -> ASGIApp:
        app = Lilya()
        app.add_middleware(SimpleInitializableMiddleware)
        app.add_middleware(NoOpMiddleware)
        return app

    app = get_app()

    with test_client_factory(app):
        pass

    assert SimpleInitializableMiddleware.counter == 1

    test_client_factory(app).get("/foo")

    assert SimpleInitializableMiddleware.counter == 1

    app = get_app()

    test_client_factory(app).get("/foo")

    assert SimpleInitializableMiddleware.counter == 2


def test_lifespan_app_subclass():
    class App(Lilya): ...

    @asynccontextmanager
    async def lifespan(app: App) -> AsyncIterator[None]:  # pragma: no cover
        yield

    App(lifespan=lifespan)
