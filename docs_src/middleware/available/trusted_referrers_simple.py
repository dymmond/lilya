from __future__ import annotations

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedreferrer import TrustedReferrerMiddleware
from lilya.routing import Include, Path
from lilya.requests import Request
from lilya.responses import Response

async def safe_get_search(request: Request) -> Response:
    search_param = ""
    if request.scope["referrer_is_trusted"]:
        search_param = request.query_params["q"]
    return Response(f"Search for {search_param}.")


routes = [Path("/", handler=safe_get_search)]


app = Lilya(routes=routes, middleware=[
    DefineMiddleware(TrustedReferrerMiddleware, allowed_referrers=["example.com"])
])
