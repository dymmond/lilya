from __future__ import annotations

import inspect
from typing import Any, TypedDict, TypeGuard

from lilya.compat import is_async_callable
from lilya.testclient._internal.types import ASGI2App, ASGI3App
from lilya.types import Receive, Scope, Send


def is_asgi3(app: ASGI2App | ASGI3App) -> TypeGuard[ASGI3App]:
    if inspect.isclass(app):
        return hasattr(app, "__await__")
    return is_async_callable(app)


class WrapASGI2:
    """
    Provide an ASGI3 interface onto an ASGI2 app.
    """

    def __init__(self, app: ASGI2App) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        instance = self.app(scope)
        await instance(receive, send)


class AsyncBackend(TypedDict):
    backend: str
    backend_options: dict[str, Any]
