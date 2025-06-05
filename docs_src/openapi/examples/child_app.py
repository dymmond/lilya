from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Leaf endpoint")
async def leaf(request):
    return {"hello": "leaf"}

# In a separate module, define a child app
child_app = Lilya(routes=[
    Path("/nested", leaf)
], enable_openapi=True)

# Mount child under /parent
app = Lilya(routes=[
    Include("/parent", app=child_app)
], enable_openapi=True)
