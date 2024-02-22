from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path


def user(): ...


app = Lilya(
    routes=[
        Path("/user", user, name="user"),
    ]
)

request = Request(...)

# Path lookup here
path = request.path_for("user")
