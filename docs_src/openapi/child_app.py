from lilya.apps import Lilya, ChildLilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Leaf endpoint")
async def leaf_handler(request):
    return {"msg": "leaf"}

# Or another Lilya app can be included as a child app
child_app = ChildLilya(routes=[
    Path("/hello", leaf_handler),
    Path("/bye", leaf_handler),
])

app = Lilya(routes=[
    Include("/child", app=child_app)
])
