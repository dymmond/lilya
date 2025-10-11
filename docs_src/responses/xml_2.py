from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import XMLResponse


async def items():
    data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    return XMLResponse(content=data)


app = Lilya(
    routes=[Path("/items", items)]
)
