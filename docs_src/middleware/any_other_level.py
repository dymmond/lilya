from typing import Any, Dict

from lilya.app import Lilya
from lilya.middleware import DefineMiddleware
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.routing import Include, Path
from lilya.types import ASGIApp, Receive, Scope, Send


class SampleMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", **kwargs):
        """SampleMiddleware Middleware class.

        The `app` is always enforced.

        Args:
            app: The 'next' ASGI app to call.
            kwargs: Any arbitrarty data.
        """
        super().__init__(app)
        self.app = app
        self.kwargs = kwargs

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Implement the middleware logic here
        """
        ...


class AnotherSample(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", **kwargs: Dict[str, Any]):
        super().__init__(app, **kwargs)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None: ...


class CustomMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", **kwargs: Dict[str, Any]):
        super().__init__(app, **kwargs)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None: ...


async def home():
    return "Hello world"


# Via Path
app = Lilya(
    routes=[Path("/", handler=home, middleware=[DefineMiddleware(AnotherSample)])],
    middleware=[DefineMiddleware(SampleMiddleware)],
)


# Via Include
app = Lilya(
    routes=[
        Include(
            "/",
            routes=[Path("/", handler=home, middleware=[DefineMiddleware(SampleMiddleware)])],
            middleware=[DefineMiddleware(CustomMiddleware)],
        )
    ],
    middleware=[DefineMiddleware(AnotherSample)],
)
