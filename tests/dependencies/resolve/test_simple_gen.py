from typing import Any

from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.testclient import create_client


def get_db():
    try:
        yield "the-session"
    finally:
        ...


async def get_params(params: dict[str, Any] = Resolve(get_db)) -> dict[str, Any]:
    return params


def test_simple(test_client_factory):
    with create_client(routes=[Path("/items", handler=get_params)]) as client:
        response = client.get("/items")

        assert response.json() == "the-session"
