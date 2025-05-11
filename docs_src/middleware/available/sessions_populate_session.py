from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request, Connection
from lilya.routing import Path


async def populate_session(con: Connection) -> dict:
    return {"id": 1, "seen_page_list": []}


async def update_session(request: Request) -> dict:
    # this updates the session
    request.scope["session"]["seen_page_list"].append("homepage")
    return request.scope["session"]


async def delete_session(request: Request) -> dict:
    old_session = request.scope["session"]
    request.scope["session"] = None
    return old_session

routes = [Path("/update", update_session), Path("/delete", delete_session)]

middleware = [DefineMiddleware(SessionMiddleware, secret_key=..., populate_session=populate_session)]

app = Lilya(routes=routes, middleware=middleware)
