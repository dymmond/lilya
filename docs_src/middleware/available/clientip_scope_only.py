from __future__ import annotations

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPScopeOnlyMiddleware
from lilya.routing import Path
from lilya.responses import Response
from lilya.requests import Request

async def echo_ip_scope(request: Request) -> Response:
    assert "x-real-ip" not in request.headers
    return Response(f"Your ip is: {request.scope['real-clientip']}")


routes = [Path("/echo", handler=echo_ip_scope)]

# Only trust unix (no client ip is set) (default)
trusted_proxies = ["unix"]
# No forwarded ip headers will be evaluated. Only the direct ip is accepted
trusted_proxies = []
# trust all client ips to provide forwarded headers
trusted_proxies = ["*"]


middleware = [DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=trusted_proxies)]

app = Lilya(routes=routes, middleware=middleware)
