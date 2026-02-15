from pydantic import BaseModel

from lilya.contrib.openapi.decorator import openapi


class CreateItemBody(BaseModel):
    name: str
    quantity: int


@openapi(summary="Create item", request_body=CreateItemBody)
async def create_item(request): ...
