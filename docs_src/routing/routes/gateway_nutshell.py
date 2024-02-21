from lilya.apps import Lilya, Request
from lilya.requests import Request
from lilya.routing import Path


async def homepage(request: Request) -> str:
    return "Hello, home!"


app = Lilya(
    routes=[
        Path(
            handler=homepage,
        )
    ]
)
