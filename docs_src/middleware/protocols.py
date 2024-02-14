from contextlib import AsyncExitStack
from typing import Optional

from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class AsyncExitStackMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp"):
        """AsyncExitStack Middleware class.

        Args:
            app: The 'next' ASGI app to call.
            config: The AsyncExitConfig instance.
        """
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if not AsyncExitStack:
            await self.app(scope, receive, send)  # pragma: no cover

        exception: Optional[Exception] = None
        async with AsyncExitStack() as stack:
            scope["lilya_astack"] = stack
            try:
                await self.app(scope, receive, send)
            except Exception as e:
                exception = e
                raise e
        if exception:
            raise exception
