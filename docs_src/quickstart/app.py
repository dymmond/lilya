from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path


async def welcome():
    return Ok({"message": "Welcome to Lilya"})


async def user(user: str):
    return Ok({"message": f"Welcome to Lilya, {user}"})


async def user_in_request(request: Request):
    user = request.path_params["user"]
    return Ok({"message": f"Welcome to Lilya, {user}"})


app = Lilya(
    routes=[
        Path("/{user}", user),
        Path("/in-request/{user}", user_in_request),
        Path("/", welcome),
    ]
)
