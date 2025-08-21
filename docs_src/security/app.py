from typing import Any

from lilya.apps import Lilya
from lilya.contrib.security.oauth2 import OAuth2PasswordBearer
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@openapi(security=[oauth2_scheme])
async def get_items(token: str = Provides()) -> dict[str, Any]:
    return {"token": token}


app = Lilya(
    routes=[
        Path("/items", handler=get_items, dependencies={"token": Provide(oauth2_scheme)}),
    ]
)
