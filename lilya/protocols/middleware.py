from __future__ import annotations

import sys

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from typing import runtime_checkable

from typing_extensions import Protocol

from lilya.types import ASGIApp, Receive, Scope, Send

P = ParamSpec("P")


@runtime_checkable
class MiddlewareProtocol(Protocol[P]):  # pragma: no cover
    __slots__ = ("app",)

    def __init__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs): ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...
