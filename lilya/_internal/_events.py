from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from lilya.compat import is_async_callable
from lilya.types import ASGIApp, Lifespan, LifespanEvent, Receive, Scope, Send

if TYPE_CHECKING:
    from lilya.routing import Router

T = TypeVar("T")


class AyncLifespanContextManager:  # pragma: no cover
    """
    Manages and handles the on_startup and on_shutdown events
    in a Lilya way.
    """

    def __init__(
        self,
        on_shutdown: LifespanEvent | None = None,
        on_startup: LifespanEvent | None = None,
    ) -> None:
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

    def __call__(self: T, app: ASGIApp | Any) -> T:
        return self

    async def __aenter__(self) -> None:
        """Runs the functions on startup"""
        for handler in self.on_startup:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def __aexit__(self, scope: Scope, receive: Receive, send: Send, **kwargs: Any) -> None:
        """Runs the functions on shutdown"""
        for handler in self.on_shutdown:
            if is_async_callable(handler):
                await handler()
            else:
                handler()


class AsyncLifespan:
    def __init__(self, router: Router):
        self.router = router

    async def __aenter__(self) -> None:
        await self.router.startup()

    async def __aexit__(self, *exc_info: object) -> None:
        await self.router.shutdown()

    def __call__(self: T, app: object) -> T:
        return self


def handle_lifespan_events(
    on_startup: LifespanEvent | None = None,
    on_shutdown: LifespanEvent | None = None,
    lifespan: Lifespan[Any] | None = None,
) -> AyncLifespanContextManager | Any | None:  # pragma: no cover
    if on_startup or on_shutdown:
        return AyncLifespanContextManager(on_startup=on_startup, on_shutdown=on_shutdown)
    elif lifespan:
        return lifespan
    return None


def generate_lifespan_events(
    on_startup: LifespanEvent | None = None,
    on_shutdown: LifespanEvent | None = None,
    lifespan: Lifespan[Any] | None = None,
) -> Any:  # pragma: no cover
    if lifespan:
        return lifespan
    return AyncLifespanContextManager(on_startup=on_startup, on_shutdown=on_shutdown)
