from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.api_key import APIKeyInHeader
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path

security = APIKeyInHeader(name="X_API_KEY")


@openapi(security=[security])
async def get_items(key: str = Provides()) -> dict[str, Any]:
    return {"key": key}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"key": Provide(security)}),
    ]
)
