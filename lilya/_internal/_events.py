from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

import anyio

from lilya._internal._inspect import func_accepts_kwargs
from lilya.compat import is_async_callable
from lilya.types import ASGIApp, Lifespan, LifespanEvent, Receive, Scope, Send

if TYPE_CHECKING:
    from lilya.routing import BaseRouter

T = TypeVar("T")


class AsyncLifespanContextManager:  # pragma: no cover
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


AyncLifespanContextManager = AsyncLifespanContextManager


class AsyncLifespan:
    def __init__(self, router: BaseRouter):
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
) -> Lifespan[Any] | None:  # pragma: no cover
    if on_startup or on_shutdown:
        return cast(
            Lifespan[Any],
            AsyncLifespanContextManager(on_startup=on_startup, on_shutdown=on_shutdown),
        )
    elif lifespan:
        return lifespan
    return None


def generate_lifespan_events(
    on_startup: LifespanEvent | None = None,
    on_shutdown: LifespanEvent | None = None,
    lifespan: Lifespan[Any] | None = None,
) -> Lifespan[Any]:  # pragma: no cover
    if lifespan:
        return lifespan
    return cast(
        Lifespan[Any], AsyncLifespanContextManager(on_startup=on_startup, on_shutdown=on_shutdown)
    )


class EventDispatcher:
    """
    A lightweight event dispatcher implementing an observable pattern.

    - Allows functions to subscribe to specific events.
    - Emits events and notifies all registered listeners asynchronously.
    - Ensures thread safety for event subscriptions and emissions.
    """

    _listeners: dict[str, list[Callable]] = {}
    _lock = anyio.Lock()  # Ensures thread-safe modifications of listeners

    @classmethod
    async def subscribe(cls, event: str, func: Callable) -> None:
        """
        Registers a function as a listener for a given event.

        - If the event does not exist, it is initialized.
        - The function is added to the list of listeners for that event.
        - Ensures safe concurrent access with a lock.

        Args:
            event (str): The name of the event to subscribe to.
            func (Callable): The function that will be triggered when the event is emitted.

        Example:
            ```python
            async def on_user_registered():
                print("User registered!")


            await EventDispatcher.subscribe("user_registered", on_user_registered)
            ```
        """
        async with cls._lock:
            if event not in cls._listeners:
                cls._listeners[event] = []
            cls._listeners[event].append(func)

    @classmethod
    async def emit(cls, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Emits an event, triggering all registered listeners asynchronously.

        - Collects all listeners for the specified event.
        - Uses `anyio.create_task_group()` to execute them concurrently.
        - Supports both synchronous and asynchronous listeners.

        Args:
            event (str): The event name to emit.
            *args (Any): Positional arguments to pass to listeners.
            **kwargs (Any): Keyword arguments to pass to listeners.

        Example:
            ```python
            async def handle_event(data):
                print(f"Received event with data: {data}")


            await EventDispatcher.subscribe("data_received", handle_event)
            await EventDispatcher.emit("data_received", {"id": 1})
            ```

        Notes:
            - Asynchronous listeners will be awaited.
            - Synchronous listeners will run in a separate thread using `anyio.to_thread.run_sync`.
        """
        async with cls._lock:
            listeners = cls._listeners.get(
                event, []
            ).copy()  # Copy to prevent modification during iteration

        async with anyio.create_task_group() as tg:
            for listener in listeners:
                if is_async_callable(listener):
                    (
                        tg.start_soon(functools.partial(listener, *args, **kwargs))
                        if func_accepts_kwargs(listener)
                        else tg.start_soon(functools.partial(listener, *args))
                    )
                else:
                    (
                        tg.start_soon(anyio.to_thread.run_sync, listener, *args, **kwargs)
                        if func_accepts_kwargs(listener)
                        else tg.start_soon(anyio.to_thread.run_sync, listener, *args)
                    )
