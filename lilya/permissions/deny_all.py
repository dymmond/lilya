from typing import ParamSpec

from lilya.exceptions import NotAuthorized
from lilya.protocols.permissions import PermissionProtocol
from lilya.types import ASGIApp, Receive, Scope, Send

P = ParamSpec("P")


class DenyAll(PermissionProtocol):
    def __init__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise NotAuthorized()
