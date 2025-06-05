from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.openapi.decorator import openapi


@openapi(summary="Hidden", include_in_schema=False)
async def hidden(request):
    ...

@openapi(summary="Visible")
async def visible_handler(request):
    ...

app = Lilya(routes=[
    Path("/visible", visible_handler),
    Path("/hidden", hidden),  # not documented
], enable_openapi=True)
