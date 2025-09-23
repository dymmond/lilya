from lilya.apps import Lilya
from lilya.routing import Path, Include
from lilya.exceptions import ContinueRouting, HTTPException


async def active_user(): ...


async def user_state_update(request):
    sniffed_msg, body_initialized = await request.sniff()
    if not body_initialized:
        raise ContinueRouting()
    try:
        jsonob = await request.json()
    except Exception: # noqa
        raise ContinueRouting()
    if jsonob.get("type") != "update_state":
        raise ContinueRouting()
    # update user state, e.g. offline, online


async def user_post_message(request):
    sniffed_msg, body_initialized = await request.sniff()
    if b'"message"' not in sniffed_msg["body"]:
        raise ContinueRouting()
    jsonob = await request.json()
    if jsonob.get("type") != "message":
        raise HTTPException(status_code=404)
    # post message for e.g. a chat

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
                    handler=user_state_update,
                    methods=["POST"]
                ),
                Path(
                    "/users/me",
                    handler=user_post_message,
                    methods=["POST"]
                )
            ],
            middleware=[...]
        ),
    ]
)
