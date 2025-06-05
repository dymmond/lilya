from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query

@openapi(
    query={
        "filter": Query(
            default={},
            schema={"type": "object", "additionalProperties": {"type": "string"}},
            description="Filter object",
            style="deepObject",
            explode=True
        )
    }
)
async def filter_items(request):
    ...
