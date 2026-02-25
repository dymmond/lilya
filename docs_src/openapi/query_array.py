from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import OpenAPIQuery


@openapi(
    query={
        "tags": OpenAPIQuery(
            default=[],
            schema={"type": "array", "items": {"type": "string"}},
            description="Filter by multiple tag names",
            style="form",
            explode=True,
        )
    }
)
async def filter_by_tags(request): ...
