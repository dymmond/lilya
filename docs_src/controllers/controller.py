from lilya.controllers import Controller
from lilya.requests import Request
from lilya.responses import Ok


class ASGIApp(Controller):

    async def get(self, request: Request):
        return Ok({"detail": "Hello, world!"})

    async def post(self):
        return Ok({"detail": "Hello, world!"})
