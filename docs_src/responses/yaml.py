from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import YAMLResponse


async def config():
    data = {"framework": "Lilya", "version": 1.0}
    return YAMLResponse(content=data)


app = Lilya(
    routes=[Path("/config", config)]
)
