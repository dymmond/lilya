from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from pydantic import BaseModel

class Item(BaseModel):
    id: str
    name: str
    description: str | None = None


@openapi(
    responses={
        201: OpenAPIResponse(model=Item, media_type="application/xml", description="Created")
    }
)
async def create_item(request):
    ...
