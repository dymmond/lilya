from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import MessagePackResponse


async def packed():
    data = {"ok": True, "value": 123}
    return MessagePackResponse(content=data)


app = Lilya(
    routes=[Path("/packed", packed)]
)
