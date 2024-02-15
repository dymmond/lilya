from lilya.app import Lilya
from lilya.exceptions import PermissionDenied
from lilya.permissions import DefinePermission
from lilya.protocols.permissions import PermissionProtocol
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.types import ASGIApp, Receive, Scope, Send


class AllowAccess(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope=scope, receive=receive, send=send)

        if "allow-access" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied()


class AdminAccess(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope=scope, receive=receive, send=send)

        if "allow-admin" in request.headers:
            await self.app(scope, receive, send)
            return
        raise PermissionDenied()


async def home():
    return "Hello world"


async def user(user: str):
    return f"Hello {user}"


# Via Path
app = Lilya(
    routes=[
        Path("/", handler=home),
        Path(
            "/{user}",
            handler=user,
            middleware=[
                DefinePermission(AdminAccess),
            ],
        ),
    ],
    middleware=[DefinePermission(AllowAccess)],
)


# Via Include
app = Lilya(
    routes=[
        Include(
            "/",
            routes=[
                Path("/", handler=home),
                Path(
                    "/{user}",
                    handler=user,
                    middleware=[
                        DefinePermission(AdminAccess),
                    ],
                ),
            ],
            middleware=[DefinePermission(AllowAccess)],
        )
    ]
)
