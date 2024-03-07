from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path


async def create(request: Request):
    await request.json()
    ...


app = Lilya(
    routes=[
        Path(
            "/create",
            handler=create,
            methods=["POST"],
        )
    ],
)
