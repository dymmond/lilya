from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.openapi.decorator import openapi

@openapi(summary="Hello endpoint")
async def say_hello(request):
    return {"message": "Hello, world!"}

app = Lilya(
    routes=[
        Path("/hello", say_hello),
    ],
    enable_openapi=True
)
