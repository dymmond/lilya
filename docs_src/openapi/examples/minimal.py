from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Ping the server")
async def ping(request):
    return {"status": "pong"}

app = Lilya(routes=[
    Path("/ping", ping)
], enable_openapi=True)
