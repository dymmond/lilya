from __future__ import annotations

from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.routing import Include
from lilya.middleware import DefineMiddleware
from lilya.middleware.session_context import SessionContextMiddleware
from lilya.middleware.sessions import SessionMiddleware

routes = [
    Include(
        "",
        routes=[],
        middleware=[
            DefineMiddleware(SessionContextMiddleware, sub_path="path1")
        ]
    ),

    Include(
        "",
        routes=[],
        middleware=[
            DefineMiddleware(SessionContextMiddleware, sub_path="path2")
        ]
    )
]

middleware = [
    DefineMiddleware(SessionMiddleware, secret="my_secret")
]

app = Lilya(routes=routes, middleware=middleware)
