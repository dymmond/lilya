from typing import Any

from typing_extensions import Protocol, runtime_checkable

from lilya.types import ASGIApp, Receive, Scope, Send


@runtime_checkable
class MiddlewareProtocol(Protocol):  # pragma: no cover
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp, **kwargs: Any):
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...
