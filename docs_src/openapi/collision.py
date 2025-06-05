from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.openapi.params import Query

@openapi(
    query={"user_id": Query(default="unused", schema={"type":"string"})}
)
async def get_user(request, user_id: str):
    ...
