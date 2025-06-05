from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query


@openapi(query={"id": Query(default="x", schema={"type":"string"})})
async def get_user(request, id: str):
    ...
# Path: /users/{id}
