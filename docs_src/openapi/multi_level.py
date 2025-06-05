from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Deep endpoint")
async def deep(request):
    return {"msg": "deep"}

app = Lilya(
    routes=[
        Include(
            "/level1",
            routes=[
                Include(
                    "/level2",
                    routes=[
                        Path(
                            "/deep", deep
                        )
                    ]
                )
            ]
        )
    ]
)
