from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Leaf endpoint")
async def leaf_handler(request):
    return {"msg": "leaf"}

app = Lilya(
    routes=[
        Include(
            "/nest",
            routes=[
                Path("/leaf", leaf_handler)
            ]
        )
    ]
)
