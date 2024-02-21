from lilya.apps import Lilya
from lilya.compat import reverse
from lilya.requests import Request
from lilya.routing import Path


def user(): ...


app = Lilya(
    routes=[
        Path("/user", user, name="user"),
    ]
)

# Path lookup here
path = reverse("user")

# Reverse with a specific app
# Path lookup here
path = reverse("user", app=app)
