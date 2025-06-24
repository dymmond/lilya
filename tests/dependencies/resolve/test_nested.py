from typing import Any

from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.testclient import create_client


async def query_params(q: str | None = None, skip: int = 0, limit: int = 20):
    return {"q": q, "skip": skip, "limit": limit}


async def get_user() -> dict[str, Any]:
    return {"username": "admin"}


async def get_user(
    user: dict[str, Any] = Resolve(get_user), params: dict[str, Any] = Resolve(query_params)
):
    return {"user": user, "params": params}


async def get_params(info: dict[str, Any] = Resolve(get_user)) -> Any:
    return info


def test_simple(test_client_factory):
    with create_client(
        routes=[
            Path(
                "/info",
                handler=get_params,
            )
        ]
    ) as client:
        response = client.get("/info")

        assert response.json() == {
            "user": {"username": "admin"},
            "params": {"q": None, "skip": 0, "limit": 20},
        }
