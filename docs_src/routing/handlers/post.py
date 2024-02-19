from lilya.app import Lilya
from lilya.requests import Request
from lilya.routing import Path


async def create(request: Request):
    # Operations to create here
    data = await request.json()
    ...


def another(name: str) -> str:
    return f"Another welcome, {name}!"


app = Lilya(
    routes=[
        Path(
            "/create",
            handler=create,
            methods=["POST"],
        ),
        Path(
            path="/last/{name:str}",
            handler=another,
            methods=["POST"],
        ),
    ]
)
