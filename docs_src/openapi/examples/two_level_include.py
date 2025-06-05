from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Deeper endpoint")
async def deeper(request):
    return {"msg": "deeper"}

app = Lilya(
    routes=[
    Include("/level1", routes=[
        Include("/level2", routes=[
            Path("/deeper", deeper)
        ])
    ])
], enable_openapi=True)
