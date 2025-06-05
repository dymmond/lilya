from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from pydantic import BaseModel

class Item(BaseModel):
    id: str
    name: str
    description: str | None = None


@openapi(
    responses={
        200: OpenAPIResponse(model=[Item], description="List of Person")
    }
)
async def list_people(request):
    ...
