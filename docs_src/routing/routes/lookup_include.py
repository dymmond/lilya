from lilya.app import Lilya
from lilya.requests import Request
from lilya.routing import Host, Include, Path, Router


def detail(): ...


app = Lilya(
    routes=[
        Path("/users/{username}", detail, name="detail"),
    ]
)

request = Request(...)

# Path lookup here
path = request.path_for("detail", username=...)
