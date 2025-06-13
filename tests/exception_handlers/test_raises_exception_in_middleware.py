from json import loads

from lilya import status
from lilya.exceptions import NotAuthorized
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.testclient import create_client


async def handle_type_error(request: Request, exc: Exception):
    status_code = status.HTTP_401_UNAUTHORIZED
    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
    return JSONResponse({"detail": details}, status_code=status_code)


class InterceptMiddleware(MiddlewareProtocol):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            raise NotAuthorized("You cannot continue from here")
        await self.app(scope, receive, send)


async def home():
    return "Welcome"


def test_cannot_access(test_client_factory):
    with create_client(
        routes=[
            Path("/home", handler=home),
        ],
        middleware=[InterceptMiddleware],
        exception_handlers={
            NotAuthorized: handle_type_error,
        },
    ) as client:
        response = client.get("/home")

        assert response.status_code == 401
        assert response.json() == {
            "detail": "401: You do not have authorization to perform this action."
        }


def test_cannot_access_using_super_class():
    with create_client(
        routes=[
            Path("/home", handler=home),
        ],
        middleware=[InterceptMiddleware],
    ) as client:
        response = client.get("/home")

        assert response.status_code == 401
        assert response.json() == {
            "detail": "You do not have authorization to perform this action.",
            "status_code": 401,
        }
