from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Root endpoint")
async def root_handler(request):
    return {"status": "ok"}

app = Lilya(
    routes=[
        Path("/", root_handler),
        Path("/health", root_handler)
    ]
)
