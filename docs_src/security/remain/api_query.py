from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.api_key import APIKeyInQuery
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path

security = APIKeyInQuery(name="api_key")


@openapi(security=[security])
async def get_items(api_key: str = Provides()) -> dict[str, Any]:
    return {"api_key": api_key}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"api_key": Provide(security)}),
    ]
)
