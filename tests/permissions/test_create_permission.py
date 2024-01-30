from lilya.permissions.base import CreatePermission, Permission
from lilya.protocols.permissions import PermissionProtocol
from lilya.responses import JSONResponse
from lilya.types import ASGIApp, Receive, Scope, Send


async def app(scope, receive, send):
    response = JSONResponse({"details": "Task started"})
    await response(scope, receive, send)


class AcceptAll(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.app(scope, receive, send)


def test_create_permission():
    obj = CreatePermission(AcceptAll)

    permission = obj(app=app)

    assert isinstance(permission, Permission)
