from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from fastapi import FastAPI, Request as FastAPIRequest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.routing import Route

from lilya._internal._middleware import ScopeIsolationMiddleware
from lilya.apps import ChildLilya, Lilya
from lilya.authentication import AuthCredentials, AuthenticationBackend, BasicUser
from lilya.middleware import DefineMiddleware
from lilya.middleware.asyncexit import AsyncExitStackMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.middleware.clientip import ClientIPMiddleware, ClientIPScopeOnlyMiddleware
from lilya.middleware.exceptions import ExceptionMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.middleware.trustedreferrer import TrustedReferrerMiddleware
from lilya.permissions import DefinePermission
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Connection, Request
from lilya.responses import JSONResponse
from lilya.routing import Include, Path
from lilya.testclient import TestClient
from lilya.types import ASGIApp, Message, Receive, Scope, Send

TestClientFactory = Callable[..., TestClient]

MISSING = "__missing__"


class SessionSnapshotMiddleware:
    def __init__(self, app: ASGIApp, header: str) -> None:
        self.app = app
        self.header = header.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                owner = scope.get("session", {}).get("owner", MISSING)
                message["headers"] = [
                    *message["headers"],
                    (self.header, str(owner).encode("latin-1")),
                ]
            await send(message)

        await self.app(scope, receive, send_wrapper)


class OuterScopeObserverMiddleware:
    def __init__(self, app: ASGIApp, key: str, header: str = "x-upstream-scope") -> None:
        self.app = app
        self.key = key
        self.header = header.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message["headers"],
                    (self.header, _scope_value(scope, self.key).encode("latin-1")),
                ]
            await send(message)

        await self.app(scope, receive, send_wrapper)


class OuterHeaderObserverMiddleware:
    def __init__(self, app: ASGIApp, header_name: str, header: str = "x-upstream-header") -> None:
        self.app = app
        self.header_name = header_name.lower()
        self.header = header.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message["headers"],
                    (
                        self.header,
                        _request_header_value(scope, self.header_name).encode("latin-1"),
                    ),
                ]
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RouteTemplateSnapshotMiddleware:
    def __init__(self, app: ASGIApp, header: str = "x-route-template") -> None:
        self.app = app
        self.header = header.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message["headers"],
                    (
                        self.header,
                        str(scope.get("route_path_template", MISSING)).encode("latin-1"),
                    ),
                ]
            await send(message)

        await self.app(scope, receive, send_wrapper)


class PositionalScopeMiddleware:
    def __init__(self, app: ASGIApp, key: str, value: str) -> None:
        self.app = app
        self.key = key
        self.value = value

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope[self.key] = self.value
        await self.app(scope, receive, send)


class PositionalScopePermission(PermissionProtocol):
    def __init__(self, app: ASGIApp, key: str, value: str) -> None:
        self.app = app
        self.key = key
        self.value = value

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope[self.key] = self.value
        await self.app(scope, receive, send)


class FixedAuthBackend(AuthenticationBackend):
    async def authenticate(self, request: Connection) -> tuple[AuthCredentials, BasicUser]:
        return AuthCredentials(["authenticated"]), BasicUser("scoped-user")


async def lilya_session_view(request: Request) -> JSONResponse:
    return JSONResponse({"session": request.session})


async def raw_session_view(scope: Scope, receive: Receive, send: Send) -> None:
    response = JSONResponse({"session": scope.get("session", {})})
    await response(scope, receive, send)


async def starlette_session_set(request: StarletteRequest) -> StarletteJSONResponse:
    request.session["owner"] = "starlette"
    return StarletteJSONResponse({"session": request.session})


async def scope_echo(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "auth": _scope_value(request.scope, "auth"),
            "clientip": _scope_value(request.scope, ClientIPScopeOnlyMiddleware.scope_name),
            "exception_handlers": request.scope.get("lilya.exception_handlers") is not None,
            "host": _scope_value(request.scope, TrustedHostMiddleware.scope_flag_name),
            "referrer": _scope_value(request.scope, TrustedReferrerMiddleware.scope_flag_name),
            "stack": request.scope.get("lilya_asyncexitstack") is not None,
            "user": _scope_value(request.scope, "user"),
            "x_real_ip": request.headers.get("x-real-ip", MISSING),
        }
    )


async def positional_scope_echo(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "middleware": request.scope.get("middleware_positional", MISSING),
            "permission": request.scope.get("permission_positional", MISSING),
        }
    )


def _scope_value(scope: Scope, key: str) -> str:
    value = scope.get(key, MISSING)
    if key == "auth" and value is not MISSING:
        return ",".join(value.scopes)
    if key == "user" and value is not MISSING:
        return value.display_name
    return str(value)


def _request_header_value(scope: Scope, header_name: str) -> str:
    headers = scope.get("headers", [])
    if hasattr(headers, "get"):
        return str(headers.get(header_name, MISSING))
    for key, value in headers:
        key = key.decode("latin-1") if isinstance(key, bytes) else key
        if key.lower() == header_name:
            return value.decode("latin-1") if isinstance(value, bytes) else value
    return MISSING


def _session_middleware(owner: str) -> DefineMiddleware:
    return DefineMiddleware(
        SessionMiddleware,
        secret_key=f"{owner}-secret",
        populate_session=lambda connection: {"owner": owner},
    )


def _include_session_middleware(owner: str, snapshot_header: str) -> list[DefineMiddleware]:
    return [
        _session_middleware(owner),
        DefineMiddleware(SessionSnapshotMiddleware, header=snapshot_header),
    ]


def test_include_session_does_not_leak_child_lilya_session_scope(
    test_client_factory: TestClientFactory,
) -> None:
    child = ChildLilya(
        routes=[Path("/view", lilya_session_view)],
        middleware=[_session_middleware("child")],
    )
    app = Lilya(
        routes=[
            Include(
                "/child",
                app=child,
                middleware=_include_session_middleware("include", "x-include-session-owner"),
            )
        ]
    )
    client = test_client_factory(app)

    response = client.get("/child/view")

    assert response.json() == {"session": {"owner": "child"}}
    assert response.headers["x-include-session-owner"] == "include"


def test_three_nested_lilya_session_middlewares_keep_their_own_scope(
    test_client_factory: TestClientFactory,
) -> None:
    leaf = ChildLilya(
        routes=[Path("/view", lilya_session_view)],
        middleware=[_session_middleware("leaf")],
    )
    middle = ChildLilya(
        routes=[Include("/leaf", app=leaf)],
        middleware=_include_session_middleware("middle", "x-middle-session-owner"),
    )
    app = Lilya(
        routes=[
            Include(
                "/middle",
                app=middle,
                middleware=_include_session_middleware("root", "x-root-session-owner"),
            )
        ]
    )
    client = test_client_factory(app)

    response = client.get("/middle/leaf/view")

    assert response.json() == {"session": {"owner": "leaf"}}
    assert response.headers["x-middle-session-owner"] == "middle"
    assert response.headers["x-root-session-owner"] == "root"


def test_include_session_does_not_leak_raw_asgi_session_scope(
    test_client_factory: TestClientFactory,
) -> None:
    raw_child = SessionMiddleware(
        raw_session_view,
        secret_key="raw-secret",
        populate_session=lambda c: {"owner": "raw"},
    )
    app = Lilya(
        routes=[
            Include(
                "/raw",
                app=raw_child,
                middleware=_include_session_middleware("include", "x-include-session-owner"),
            )
        ]
    )
    client = test_client_factory(app)

    response = client.get("/raw/view")

    assert response.json() == {"session": {"owner": "raw"}}
    assert response.headers["x-include-session-owner"] == "include"


def test_include_session_preserves_starlette_child_session_scope(
    test_client_factory: TestClientFactory,
) -> None:
    starlette_app = Starlette(routes=[Route("/set", starlette_session_set, methods=["POST"])])
    starlette_app.add_middleware(StarletteSessionMiddleware, secret_key="starlette-secret")
    app = Lilya(
        routes=[
            Include(
                "/starlette",
                app=starlette_app,
                middleware=_include_session_middleware("include", "x-include-session-owner"),
            )
        ]
    )
    client = test_client_factory(app)

    response = client.post("/starlette/set")

    assert response.json() == {"session": {"owner": "starlette"}}
    assert response.headers["x-include-session-owner"] == "include"


def test_include_session_preserves_fastapi_child_session_scope(
    test_client_factory: TestClientFactory,
) -> None:
    fastapi_app = FastAPI()
    fastapi_app.add_middleware(StarletteSessionMiddleware, secret_key="fastapi-secret")

    @fastapi_app.post("/set")
    async def fastapi_session_set(request: FastAPIRequest) -> dict[str, dict[str, Any]]:
        request.session["owner"] = "fastapi"
        return {"session": request.session}

    app = Lilya(
        routes=[
            Include(
                "/fastapi",
                app=fastapi_app,
                middleware=_include_session_middleware("include", "x-include-session-owner"),
            )
        ]
    )
    client = test_client_factory(app)

    response = client.post("/fastapi/set")

    assert response.json() == {"session": {"owner": "fastapi"}}
    assert response.headers["x-include-session-owner"] == "include"


def test_route_metadata_is_available_to_response_side_middleware(
    test_client_factory: TestClientFactory,
) -> None:
    app = Lilya(
        routes=[Path("/items/{item_id}", scope_echo)],
        middleware=[DefineMiddleware(RouteTemplateSnapshotMiddleware)],
    )
    client = test_client_factory(app)

    response = client.get("/items/123")

    assert response.status_code == 200
    assert response.headers["x-route-template"] == "/items/{item_id}"


def test_route_metadata_is_preserved_when_child_raises() -> None:
    async def raising_app(scope: Scope, receive: Receive, send: Send) -> None:
        scope["route_path_template"] = "/raised"
        raise RuntimeError("boom")

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        pass

    scope: Scope = {"type": "http", "headers": []}
    isolated_app = ScopeIsolationMiddleware(raising_app)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(isolated_app(scope, receive, send))

    assert scope["route_path_template"] == "/raised"


def test_route_metadata_syncs_once_for_streaming_messages() -> None:
    sync_count = 0

    class CountingScopeIsolationMiddleware(ScopeIsolationMiddleware):
        def sync_route_metadata(self, source_scope: Scope, target_scope: Scope) -> None:
            nonlocal sync_count
            sync_count += 1
            super().sync_route_metadata(source_scope, target_scope)

    async def streaming_app(scope: Scope, receive: Receive, send: Send) -> None:
        scope["route_path_template"] = "/stream"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"one", "more_body": True})
        await send({"type": "http.response.body", "body": b"two", "more_body": False})

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    observed_route_templates = []

    async def send(message: Message) -> None:
        observed_route_templates.append(scope.get("route_path_template", MISSING))

    scope: Scope = {"type": "http", "headers": []}
    isolated_app = CountingScopeIsolationMiddleware(streaming_app)

    asyncio.run(isolated_app(scope, receive, send))

    assert observed_route_templates == ["/stream", "/stream", "/stream"]
    assert scope["route_path_template"] == "/stream"
    assert sync_count == 2


def test_middleware_and_permission_positional_arguments_are_supported(
    test_client_factory: TestClientFactory,
) -> None:
    app = Lilya(
        routes=[Path("/", positional_scope_echo)],
        middleware=[
            DefineMiddleware(
                PositionalScopeMiddleware,
                "middleware_positional",
                "middleware-value",
            )
        ],
        permissions=[
            DefinePermission(
                PositionalScopePermission,
                "permission_positional",
                "permission-value",
            )
        ],
    )
    client = test_client_factory(app)

    response = client.get("/")

    assert response.json() == {
        "middleware": "middleware-value",
        "permission": "permission-value",
    }


@pytest.mark.parametrize(
    ("middleware", "scope_key", "response_key", "expected"),
    [
        (
            [DefineMiddleware(AuthenticationMiddleware, backend=FixedAuthBackend())],
            "user",
            "user",
            "scoped-user",
        ),
        (
            [DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=["unix"])],
            ClientIPScopeOnlyMiddleware.scope_name,
            "clientip",
            "203.0.113.10",
        ),
        (
            [DefineMiddleware(ExceptionMiddleware)],
            "lilya.exception_handlers",
            "exception_handlers",
            True,
        ),
        (
            [DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["testserver"])],
            TrustedHostMiddleware.scope_flag_name,
            "host",
            "True",
        ),
        (
            [DefineMiddleware(TrustedReferrerMiddleware, allowed_referrers=[""])],
            TrustedReferrerMiddleware.scope_flag_name,
            "referrer",
            "True",
        ),
        (
            [DefineMiddleware(AsyncExitStackMiddleware)],
            "lilya_asyncexitstack",
            "stack",
            True,
        ),
    ],
)
def test_scope_writing_middlewares_do_not_leak_to_upstream_scope(
    test_client_factory: TestClientFactory,
    middleware: Sequence[DefineMiddleware],
    scope_key: str,
    response_key: str,
    expected: Any,
) -> None:
    app = Lilya(
        routes=[Path("/", scope_echo)],
        middleware=[
            DefineMiddleware(OuterScopeObserverMiddleware, key=scope_key),
            *middleware,
        ],
    )
    client = test_client_factory(app)

    headers = {"x-forwarded-for": "203.0.113.10"} if response_key == "clientip" else None
    response = client.get("/", headers=headers)

    assert response.json()[response_key] == expected
    assert response.headers["x-upstream-scope"] == MISSING


def test_clientip_header_middleware_does_not_leak_header_to_upstream_scope(
    test_client_factory: TestClientFactory,
) -> None:
    app = Lilya(
        routes=[Path("/", scope_echo)],
        middleware=[
            DefineMiddleware(OuterHeaderObserverMiddleware, header_name="x-real-ip"),
            DefineMiddleware(ClientIPMiddleware, trusted_proxies=["unix"]),
        ],
    )
    client = test_client_factory(app)

    response = client.get("/", headers={"x-forwarded-for": "203.0.113.10"})

    assert response.json()["x_real_ip"] == "203.0.113.10"
    assert response.headers["x-upstream-header"] == MISSING
