from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query

@openapi(
    query={"limit": Query(default=10, schema={"type": "integer"}, description="Max items to return")}
)
async def get_items(request):
    ...
