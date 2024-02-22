from lilya.apps import Lilya
from lilya.responses import JSONResponse
from lilya.routing import Path


async def example():
    return JSONResponse({"message": "Welcome home!"})


def another():
    return "Another welcome!"


def another_read(name: str):
    return f"Another welcome, {name}!"


app = Lilya(
    routes=[
        Path(
            "/",
            handler=example,
            methods=["HEAD"],
        ),
        Path(
            "/another",
            handler=another,
            methods=["HEAD"],
        ),
        Path(
            "/last/{name:str}",
            handler=another_read,
            methods=["HEAD"],
        ),
    ]
)
