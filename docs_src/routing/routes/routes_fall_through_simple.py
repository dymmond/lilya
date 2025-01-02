from lilya.apps import Lilya
from lilya.routing import Path, Include


async def active_user(): ...


async def user_post(): ...


async def list_user(): ...


app = Lilya(
    routes=[
        Include(
            "/",
            name="get",
            routes=[
                Path(
                    "/users",
                    handler=list_user,
                ),
                Path(
                    "/users/me",
                    handler=active_user,
                )
            ]
        ),
        Include(
            "/",
            name="logged_in",
            routes=[
                Path(
                    "/users/me",
                    handler=user_post,
                    methods=["POST"]
                ),
                Path(
                    "/users/me",
                    handler=user_post2,
                    methods=["POST"]
                )
            ],
            middleware=[...]
        ),
    ]
)
