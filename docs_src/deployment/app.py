from __future__ import annotations

from lilya.apps import Lilya
from lilya.routing import Path


def home():
    return {"Hello": "World"}


def read_user(user_id: int, q: str | None = None):
    return {"item_id": user_id, "q": q}


app = Lilya(
    routes=[
        Path("/", handler=home),
        Path("/users/{user_id}", handler=read_user),
    ]
)
