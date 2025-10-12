from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import EventStreamResponse
import asyncio


async def events():
    async def event_generator():
        for i in range(3):
            yield {"event": "tick", "data": {"count": i}}
            await asyncio.sleep(1)
        yield {"event": "done", "data": "Stream finished"}

    return EventStreamResponse(event_generator())


app = Lilya(
    routes=[Path("/events", events)]
)
