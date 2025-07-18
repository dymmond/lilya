from typing import Any

from lilya.controllers import Controller
from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.testclient import create_client


async def query_params(q: str | None = None, skip: int = 0, limit: int = 20) -> dict[str, Any]:
    return {"q": q, "skip": skip, "limit": limit}


class Test(Controller):
    async def get(self, params: dict[str, Any] = Resolve(query_params)) -> dict[str, Any]:
        return params


def test_simple(test_client_factory):
    with create_client(routes=[Path("/items", handler=Test)]) as client:
        response = client.get("/items")

        assert response.json() == {"q": None, "skip": 0, "limit": 20}
