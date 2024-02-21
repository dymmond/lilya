from lilya.apps import Lilya
from lilya.routing import Path


async def user(): ...


async def active_user(): ...


# Don't do this: `/users/me`` will never match the incoming requests.
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

# Do this: `/users/me` is tested first and both cases will work.
app = Lilya(
    routes=[
        Path(
            "/users/me",
            handler=active_user,
        ),
        Path(
            "/users/{username}",
            handler=user,
        ),
    ]
)
