from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.open_id import OpenIdConnect
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path


security = OpenIdConnect(openIdConnectUrl="/openid", description="OpenIdConnect security scheme")


@openapi(security=[security])
async def get_items(auth: str = Provides()) -> dict[str, Any]:
    return {"auth": auth}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"auth": Provide(security)}),
    ]
)
