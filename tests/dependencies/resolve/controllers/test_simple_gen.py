from typing import Any

from lilya.controllers import Controller
from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.testclient import create_client


def get_db():
    try:
        yield "the-session"
    finally:
        ...


class Test(Controller):
    async def get(self, params: dict[str, Any] = Resolve(get_db)) -> dict[str, Any]:
        return params


def test_simple(test_client_factory):
    with create_client(routes=[Path("/items", handler=Test)]) as client:
        response = client.get("/items")

        assert response.json() == "the-session"
