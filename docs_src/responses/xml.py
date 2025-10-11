from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import XMLResponse


async def feed():
    data = {"person": {"name": "Lilya", "age": 35}}
    return XMLResponse(content=data)


app = Lilya(
    routes=[Path("/feed", feed)]
)
