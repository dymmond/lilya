from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.api_key import APIKeyInCookie
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path


security = APIKeyInCookie(name="session")


@openapi(security=[security])
async def get_items(session: str = Provides()) -> dict[str, Any]:
    return {"session": session}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"session": Provide(security)}),
    ]
)
