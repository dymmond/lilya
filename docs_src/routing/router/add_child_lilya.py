from lilya.apps import ChildLilya, Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path, Router


async def home() -> str:
    return "home"


child = ChildLilya(
    routes=[
        Path("/", handler=home, name="view"),
    ]
)

app = Lilya()

app.add_child_lilya(
    path="/child",
    child=child,
    name=...,
    middleware=...,
    permissions=...,
    include_in_schema=...,
    deprecated=...,
)
