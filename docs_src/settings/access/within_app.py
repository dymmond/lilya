from lilya.app import Lilya
from lilya.requests import Request
from lilya.routing import Path


async def app_debug(request: Request):
    settings = request.app.settings
    return {"debug": settings.debug}


app = Lilya(routes=[Path("/", app_debug)])
