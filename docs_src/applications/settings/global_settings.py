from lilya.app import Lilya
from lilya.conf import settings
from lilya.routing import Path


async def app_debug():
    return {"debug": settings.debug}


app = Lilya(routes=[Path("/", app_debug)])
