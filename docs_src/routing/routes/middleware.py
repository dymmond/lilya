from lilya.app import Lilya
from lilya.middleware import DefineMiddleware
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.routing import Path
from lilya.types import ASGIApp


class RequestLoggingMiddlewareProtocol(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", kwargs: str = "") -> None:
        self.app = app
        self.kwargs = kwargs


class ExampleMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp") -> None:
        self.app = app


async def homepage():
    return {"page": "ok"}


app = Lilya(
    routes=[
        Path(
            "/home",
            handler=homepage,
            middleware=[DefineMiddleware(ExampleMiddleware)],
        )
    ],
    middleware=[
        DefineMiddleware(RequestLoggingMiddlewareProtocol),
    ],
)
