from typing import Any, Dict

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
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
        # optional helper to manipulate/parse the headers and keep them in the scope
        header_instance = Header.ensure_header_instance(scope)
        ...


class AnotherSample(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", **kwargs: Dict[str, Any]):
        super().__init__(app, **kwargs)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        await self.app(scope, receive, send)


app = Lilya(
    routes=[...],
    middleware=[
        DefineMiddleware(SampleMiddleware),
        DefineMiddleware(AnotherSample),
    ],
)
