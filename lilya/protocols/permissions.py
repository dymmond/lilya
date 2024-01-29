from typing import ParamSpec

from typing_extensions import Protocol, runtime_checkable

from lilya.types import ASGIApp, Receive, Scope, Send

P = ParamSpec("P")


@runtime_checkable
class PermissionProtocol(Protocol[P]):  # pragma: no cover
    __slots__ = ("app",)

    def __init__(self, app: "ASGIApp", *args: P.args, **kwargs: P.kwargs): ...

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None: ...
