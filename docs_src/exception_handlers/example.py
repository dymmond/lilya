from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path


async def create(request: Request):
    data = await request.json()
    if len(data) == 0:
        raise ValueError("Cannot be 0.")


app = Lilya(
    routes=[
        Path(
            "/create",
            handler=create,
            methods=["POST"],
        )
    ],
)
