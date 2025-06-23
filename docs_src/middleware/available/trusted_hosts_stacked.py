from __future__ import annotations


from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.requests import Request


async def example_host_trust_switch(request: Request) -> JSONResponse:
    if request.scope["host_is_trusted"]:
        return JSONResponse({"message": "Welcome home!"})
    else:
        return JSONResponse({"message": "Welcome stranger!"})


routes = [Path("/", handler=example_host_trust_switch)]

middleware = [
    DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["www.example.com", "*.example.com", "example.intern"]),
    DefineMiddleware(TrustedHostMiddleware, allowed_hosts=["example.intern"], block_untrusted_hosts=False)
]

app = Lilya(routes=routes, middleware=middleware)
