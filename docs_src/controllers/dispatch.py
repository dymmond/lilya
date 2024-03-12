from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.responses import Ok, Response
from lilya.routing import Path


class ASGIAppController(Controller):
    async def get(self):
        return Response("Hello, World!")


class AuthController(Controller):
    async def get(self, username: str):
        return Ok({"message": f"Hello, {username}"})


app = Lilya(
    routes=[
        Path("/", handler=ASGIAppController),
        Path("/{username}", handler=AuthController),
    ]
)
