from typing import Any

from typing import Any
from lilya.dependencies import Resolve, Provide, Provides
from lilya.routing import Path
from lilya.apps import Lilya
from lilya.responses import JSONResponse


async def get_user():
    return {"id": 1, "name": "Alice"}


async def get_current_user(user: Any = Resolve(get_user)):
    return user


async def get_items(current_user: Any = Provides()) -> JSONResponse:
    return JSONResponse({"message": "Hello", "user": current_user})


app = Lilya(
    routes=[
        Path(
            "/items", handler=get_items,
            dependencies={
                "current_user": Provide(get_current_user)
            },
        ),
    ]
)