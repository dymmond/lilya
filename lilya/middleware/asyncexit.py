from __future__ import annotations

import traceback
from contextlib import AsyncExitStack
from typing import Any

from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send


class AsyncExitStackMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, debug: bool = False) -> None:
        """AsyncExitStack Middleware class.

        Args:
            app: The 'next' ASGI app to call.
        """
        self.app = app
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not AsyncExitStack:
            await self.app(scope, receive, send)  # pragma: no cover

        stack = _LazyAsyncExitStack()
        scope["lilya_asyncexitstack"] = stack
        exception: Exception | None = None
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            exception = e
        finally:
            await stack.aclose()

        if exception and self.debug:
            traceback.print_exception(exception, exception, exception.__traceback__)  # type: ignore

        if exception:
            raise exception


class _LazyAsyncExitStack:
    __slots__ = ("_stack",)

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None

    def _ensure(self) -> AsyncExitStack:
        if self._stack is None:
            self._stack = AsyncExitStack()
        return self._stack

    async def aclose(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()

    def __getattr__(self, item: str) -> Any:
        return getattr(self._ensure(), item)
