from lilya.app import Lilya
from lilya.compat import reverse
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
path = reverse(
    "users:detail",
    path_params={"username": ...},
)

# Reverse with a specific app
# Path lookup here
path = reverse(
    "users:detail",
    app=app,
    path_params={"username": ...},
)
