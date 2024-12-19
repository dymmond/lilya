from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request
from lilya.routing import Path


async def set_session(request: Request) -> dict:
    # this creates/updates the session
    if not request.scope["session"]:
        request.scope["session"] = {"id": 1, "seen_page_list": []}
    else:
        # this updates the session
        request.scope["session"]["seen_page_list"].append("homepage")
    return request.scope["session"]


async def delete_session(request: Request) -> dict:
    old_session = request.scope["session"]
    request.scope["session"] = None
    return old_session

routes = [Path("/set", set_session), Path("/delete", delete_session)]

# Option one
middleware = [DefineMiddleware(SessionMiddleware, secret_key=...)]

app = Lilya(routes=routes, middleware=middleware)


# Option two - Using the settings module
# Running the application with your custom settings -> LILYA_SETTINGS_MODULE
@dataclass
class AppSettings(Settings):
    @property
    def middleware(self) -> list[DefineMiddleware]:
        return [
            DefineMiddleware(SessionMiddleware, secret_key=...),
        ]
