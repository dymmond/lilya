from lilya.apps import Lilya
from lilya.routing import Path
from lilya.exceptions import ContinueRouting


async def user(username: str):
    if username == "me":
        raise ContinueRouting()


async def active_user(): ...


# This way the former example works
app = Lilya(
    routes=[
        Path(
            "/users/{username}",
            handler=user,
        ),
        Path(
            "/users/me",
            handler=active_user,
        ),
    ]
)
