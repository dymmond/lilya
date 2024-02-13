from lilya.app import Lilya
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path


def welcome():
    return Ok({"message": "Welcome to Lilya"})


def user(user: str):
    return Ok({"message": f"Welcome to Lilya, {user}"})


def user_in_request(request: Request):
    user = request.path_params["user"]
    return Ok({"message": f"Welcome to Lilya, {user}"})


app = Lilya(
    routes=[
        Path("/", welcome),
        Path("/{user}", user),
        Path("/in-request/{user}", user_in_request),
    ]
)
