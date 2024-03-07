from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path


def detail(): ...


app = Lilya(
    routes=[
        Path("/users/{username}", detail, name="detail"),
    ]
)

request = Request(...)

# Path lookup here
path = request.path_for("detail", username=...)
