
from lilya.types import ASGIApp, Scope, Receive, Send
from lilya.protocols.permissions import PermissionProtocol

class MyPermission(PermissionProtocol)  :
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.app(scope, receive, send)
