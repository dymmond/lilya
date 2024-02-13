from lilya.enums import ScopeType
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.types import Receive, Scope, Send


async def app(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == ScopeType.HTTP

    request = Request(scope=scope, receive=receive, send=send)
    data = "{} {}".format(request.method, request.url.path)

    response = PlainText(content=data)
    await response(scope, receive, send)
