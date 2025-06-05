from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from pydantic import BaseModel

class Item(BaseModel):
    id: str
    name: str
    description: str | None = None


class ErrorModel(BaseModel):
    detail: str
    code: int

@openapi(
    responses={
        200: OpenAPIResponse(model=Item, description="An Item"),
        400: OpenAPIResponse(model=ErrorModel, description="Item not found"),
    }
)
async def get_item(request, item_id: str):
    ...
