from __future__ import annotations

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPScopeOnlyMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.middleware.session_fixing import SessionFixingMiddleware
from lilya.routing import Path
from lilya.responses import Response
from lilya.requests import Request
from typing import Any

async def echo_ip_scope(request: Request) -> Response:
    assert "x-real-ip" not in request.headers
    return Response(f"Your ip is: {request.scope['real-clientip']}")


routes = [Path("/echo", handler=echo_ip_scope)]

# Only trust unix (no client ip is set) (default)
trusted_proxies = ["unix"]

def notify_fn(old_ip: str | None, new_ip: str, old_session: dict, new_session: dict) -> None:
    if old_ip is None:
        print(f'New session for ip: "{new_ip}".')
    else:
        print(f'Replace session for ip: "{old_ip}". Has new ip "{new_ip}".')

middleware = [
    DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=trusted_proxies),
    DefineMiddleware(SessionMiddleware, secret_key=...),
    DefineMiddleware(SessionFixingMiddleware,notify_fn=notify_fn)
]

app = Lilya(routes=routes, middleware=middleware)
