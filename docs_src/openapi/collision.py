from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import OpenAPIQuery


@openapi(query={"user_id": OpenAPIQuery(default="unused", schema={"type": "string"})})
async def get_user(request, user_id: str): ...
