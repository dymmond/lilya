from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

class ErrorModel(BaseModel):
    detail: str

@openapi(
    summary="List items",
    description="Return a paginated list of items",
    query={
        "limit": Query(default=10, schema={"type": "integer"}, description="Max items"),
        "tags": Query(
            default=[],
            schema={"type":"array","items":{"type":"string"}},
            style="form",
            explode=True,
            description="Filter by tags"
        ),
    },
    responses={
        200: OpenAPIResponse(model=[Item], description="List of items"),
        400: OpenAPIResponse(model=ErrorModel, description="Invalid parameters")
    }
)
async def list_items(request):
    ...


app = Lilya(routes=[
    Path(
        "/items", list_items
    )],
    enable_openapi=True
)
