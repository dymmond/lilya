from __future__ import annotations

from typing import Any, ParamSpec, Protocol, _ProtocolMeta, runtime_checkable

from lilya.types import ASGIApp, Receive, Scope, Send

P = ParamSpec("P")


class MetaMiddleware(_ProtocolMeta):
    def __call__(cls, app: ASGIApp, *args: Any, **kwargs: Any) -> Any:
        instance = super().__call__(app, *args, **kwargs)
        if hasattr(app, "__is_controller__"):
            instance.app = app()  # type: ignore
        else:
            instance.app = app
        return instance


@runtime_checkable
class MiddlewareProtocol(Protocol[P], metaclass=MetaMiddleware):  # pragma: no cover
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs) -> None: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...
