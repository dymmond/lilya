from lilya.controllers import Controller
from lilya.exceptions import NotAuthorized, PermissionDenied
from lilya.middleware import DefineMiddleware
from lilya.permissions import DefinePermission
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class CustomMiddleware(MiddlewareProtocol):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive, send=send)
        if "X-Custom-Header" not in request.headers:
            raise NotAuthorized(detail="Missing X-Custom-Header")
        await self.app(scope, receive, send)


class CustomPermission(PermissionProtocol):
    def __init__(
        self,
        app,
    ):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope, receive, send):
        request = Request(scope=scope, receive=receive, send=send)
        if "allow-access" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied(detail="Access Denied by CustomPermission")


async def simple_endpoint():
    return {"message": "Hello, World!"}


class SimpleController(Controller):
    middleware = [DefineMiddleware(CustomMiddleware)]

    async def get(self):
        return {"message": "Hello, World!"}


def test_middleware_on_controller():
    with create_client(
        routes=[
            Path("/", SimpleController),
        ],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"detail": "Missing X-Custom-Header"}


class SimpleControllerPath(Controller):
    async def get(self):
        return {"message": "Hello, World!"}


def test_middleware_on_controller_path():
    with create_client(
        routes=[
            Path("/", SimpleControllerPath, middleware=[DefineMiddleware(CustomMiddleware)]),
        ],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"detail": "Missing X-Custom-Header"}


class ComplexController(Controller):
    middleware = [DefineMiddleware(CustomMiddleware)]
    permissions = [DefinePermission(CustomPermission)]

    async def get(self):
        return {"message": "Hello, World!"}


class ComplexControllerPath(Controller):
    async def get(self):
        return {"message": "Hello, World!"}


def test_middleware_with_permission_on_controller():
    with create_client(
        routes=[
            Path(
                "/",
                ComplexControllerPath,
                middleware=[DefineMiddleware(CustomMiddleware)],
                permissions=[DefinePermission(CustomPermission)],
            ),
        ],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"detail": "Missing X-Custom-Header"}

        # Test with custom header but without permission header
        response = client.get("/", headers={"X-Custom-Header": "value"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Access Denied by CustomPermission"}

        # Test with both headers
        response = client.get("/", headers={"X-Custom-Header": "value", "allow-access": "true"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}


def test_middleware_triggers_first_then_permission_top_level():
    with create_client(
        routes=[
            Path("/", simple_endpoint),
        ],
        middleware=[DefineMiddleware(CustomMiddleware)],
        permissions=[DefinePermission(CustomPermission)],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"status_code": 401, "detail": "Missing X-Custom-Header"}

        # Test with custom header but without permission header
        response = client.get("/", headers={"X-Custom-Header": "value"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Access Denied by CustomPermission"}

        # Test with both headers
        response = client.get("/", headers={"X-Custom-Header": "value", "allow-access": "true"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}


def test_middleware_triggers_first_then_permission_include():
    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path("/", simple_endpoint),
                ],
                middleware=[DefineMiddleware(CustomMiddleware)],
                permissions=[DefinePermission(CustomPermission)],
            ),
        ],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"detail": "Missing X-Custom-Header"}

        # Test with custom header but without permission header
        response = client.get("/", headers={"X-Custom-Header": "value"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Access Denied by CustomPermission"}

        # Test with both headers
        response = client.get("/", headers={"X-Custom-Header": "value", "allow-access": "true"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}


def test_middleware_triggers_first_then_permission_path():
    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path(
                        "/",
                        simple_endpoint,
                        middleware=[DefineMiddleware(CustomMiddleware)],
                        permissions=[DefinePermission(CustomPermission)],
                    ),
                ],
            ),
        ],
        settings_module=EncoderSettings,
    ) as client:
        # Test without custom header
        response = client.get("/")
        assert response.status_code == 401
        assert response.json() == {"detail": "Missing X-Custom-Header"}

        # Test with custom header but without permission header
        response = client.get("/", headers={"X-Custom-Header": "value"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Access Denied by CustomPermission"}

        # Test with both headers
        response = client.get("/", headers={"X-Custom-Header": "value", "allow-access": "true"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, World!"}
