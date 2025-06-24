from typing import Any
from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.apps import Lilya



async def query_params(q: str | None = None, skip: int = 0, limit: int = 20):
    return {"q": q, "skip": skip, "limit": limit}


async def get_user() -> dict[str, Any]:
    return {"username": "admin"}


async def get_user(
    user: dict[str, Any] = Resolve(get_user), params: dict[str, Any] = Resolve(query_params)
):
    return {"user": user, "params": params}


async def get_info(info: dict[str, Any] = Resolve(get_user)) -> Any:
    return info


app = Lilya(
    routes=[Path("/info", handler=get_info)],
)