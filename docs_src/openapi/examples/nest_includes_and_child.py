from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Leaf endpoint")
async def leaf(request):
    return {"hello": "leaf"}

app = Lilya(
    routes=[
        Include(
            "/api",
            routes=[
                Path(
                    "/leaf", leaf
                )
            ]
        )
    ],
    enable_openapi=True
)
