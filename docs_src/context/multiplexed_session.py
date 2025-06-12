
from lilya.apps import Lilya
from lilya.context import session
from lilya.middleware import DefineMiddleware
from lilya.middleware.session_context import SessionContextMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.routing import Path


async def home() -> dict:
    session["visits"] = session.get("visits", 0) + 1
    return {"visits": session["visits"]}


app = Lilya(routes=[
        Path('/show1', home, middleware=[DefineMiddleware(SessionContextMiddleware, sub_path="home1")]),
        Path('/show2', home, middleware=[DefineMiddleware(SessionContextMiddleware, sub_path="home2")])
    ],
    middleware=[
        DefineMiddleware(SessionMiddleware, secret='my_secret'),
    ],
)
