from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import EventStreamResponse
import asyncio


async def stream():
    async def counter():
        for i in range(1, 6):
            yield {"event": "count", "data": {"value": i}}
            await asyncio.sleep(0.5)
        yield {"event": "complete", "data": "Counter finished"}

    return EventStreamResponse(counter(), retry=3000)


app = Lilya(
    routes=[Path("/stream", stream)]
)
