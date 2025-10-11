from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import NDJSONResponse


async def read_data():
    data = [
        {"event": "start"},
        {"event": "progress"},
        {"event": "done"},
    ]
    return NDJSONResponse(data)

app = Lilya(
    routes=[Path("/read", read_data)]
)
