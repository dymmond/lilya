from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.http import HTTPBearer, HTTPAuthorizationCredentials
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path

security = HTTPBearer()


@openapi(security=[security])
async def get_items(credentials: HTTPAuthorizationCredentials = Provides()) -> dict[str, Any]:
    return {"scheme": credentials.scheme, "credentials": credentials.credentials}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"auth": Provide(security)}),
    ]
)
