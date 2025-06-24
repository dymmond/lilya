from typing import Any


from typing import Any
from lilya.dependencies import Resolve
from lilya.routing import Path
from lilya.apps import Lilya


async def query_params(q: str | None = None, skip: int = 0, limit: int = 20):
    return {"q": q, "skip": skip, "limit": limit}


async def get_params(params: dict[str, Any] = Resolve(query_params)) -> Any:
    return params


app = Lilya(
    routes=[Path("/items", handler=get_params)],
)
