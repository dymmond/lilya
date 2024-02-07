from lilya.exceptions import PermissionDenied
from lilya.permissions import DefinePermission
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Include, Path
from lilya.testclient import create_client
from lilya.types import ASGIApp, Receive, Scope, Send


def home():
    return {"message": "Welcome home"}


def user(user: str):
    return Ok({"message": f"Welcome {user}"})


class DenyAccess(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        raise PermissionDenied()


class AllowAccess(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive, send=send)

        if "allow-admin" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied()


def test_add_permission_on_top_level_app(test_client_factory):
    with create_client(
        routes=[
            Path("/", home),
            Path("/{user}", user),
        ],
        permissions=[DefinePermission(DenyAccess)],
    ) as client:
        response = client.get("/")

        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."

        response = client.get("/lilya")
        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."


def test_add_permission_allowing_access(test_client_factory):
    with create_client(
        routes=[
            Path("/", home),
            Path("/{user}", user),
        ],
        permissions=[DefinePermission(AllowAccess)],
    ) as client:

        headers = {"allow-admin": "true"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome home"}

        response = client.get("/lilya")
        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."


class AllowPathAccess(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope=scope, receive=receive, send=send)

        if "allow-admin" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied()


def test_add_permission_on_path(test_client_factory):
    with create_client(
        routes=[
            Path(
                "/",
                home,
                permissions=[DefinePermission(AllowPathAccess)],
            ),
            Path(
                "/{user}",
                user,
                permissions=[DefinePermission(AllowPathAccess)],
            ),
        ],
    ) as client:

        headers = {"allow-admin": "true"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome home"}

        response = client.get("/lilya")
        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."


def test_add_permission_on_include(test_client_factory):
    with create_client(
        routes=[
            Include(
                "/include",
                routes=[
                    Path("/", home),
                    Path("/{user}", user),
                ],
                permissions=[DefinePermission(AllowPathAccess)],
            ),
        ],
    ) as client:

        headers = {"allow-admin": "true"}
        response = client.get("/include", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome home"}

        response = client.get("/include/lilya")
        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."


class AllowRawAccess:
    def __init__(self, app: ASGIApp, *args, **kwargs):
        self.app = app
        self.args = args
        self.kwargs = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope=scope, receive=receive, send=send)

        if "allow-admin" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied()


def test_add_permission_on_include_raw_permission(test_client_factory):
    with create_client(
        routes=[
            Include(
                "/include",
                routes=[
                    Path("/", home),
                    Path("/{user}", user),
                ],
                permissions=[DefinePermission(AllowRawAccess)],
            ),
        ],
    ) as client:

        headers = {"allow-admin": "true"}
        response = client.get("/include", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome home"}

        response = client.get("/include/lilya")
        assert response.status_code == 403
        assert response.text == "You do not have permission to perform this action."
