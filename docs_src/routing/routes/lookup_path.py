from lilya.app import Lilya
from lilya.requests import Request
from lilya.routing import Include, Path


def detail(): ...


app = Lilya(
    routes=[
        Include(
            "/users",
            routes=[
                Path("/{username}", detail, name="detail"),
            ],
            name="users",
        )
    ]
)

request = Request(...)

# Path lookup here
path = request.path_for("users:detail", username=...)
