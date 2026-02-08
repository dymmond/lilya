from lilya.apps import Lilya, ChildLilya
from lilya.routing import Path, Include
from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from pydantic import BaseModel


# Pydantic models
class Item(BaseModel):
    id: int
    name: str


class Person(BaseModel):
    first_name: str
    last_name: str


# Handlers
@openapi(
    summary="Get items for a user",
    description="Returns a list of items belonging to a specific user.",
    query={
        "limit": Query(default=5, schema={"type": "integer"}, description="Max items"),
        "tags": Query(
            default=[],
            schema={"type": "array", "items": {"type": "string"}},
            style="form",
            explode=True,
            description="Tags filter",
        ),
    },
    responses={
        200: OpenAPIResponse(model=[Item], description="Array of Item"),
        404: OpenAPIResponse(model=Person, description="User not found"),
    },
    tags=["items", "users"],
    security=[
        {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}
    ],
)
async def list_user_items(request, user_id: str): ...


@openapi(
    summary="Create a new item",
    request_body=Item,
)
async def create_item(request, user_id: str, item: Item): ...


# Build app with nested includes and a child app
child = ChildLilya(routes=[Path("/profile", list_user_items)], enable_openapi=True)


app = Lilya(
    routes=[
        Include(
            "/users",
            routes=[
                Path("/{user_id}/items", list_user_items),
                Path("/{user_id}/items/create", create_item),
                Include("/extra", routes=[Path("/{user_id}/extra-info", create_item)]),
            ],
        ),
        Include("/account", app=child),
    ],
    enable_openapi=True,
)
