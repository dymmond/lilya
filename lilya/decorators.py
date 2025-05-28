from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

import anyio
from anyio.from_thread import start_blocking_portal

from lilya._internal._events import EventDispatcher  # noqa
from lilya.compat import is_async_callable


def observable(send: list[str] | None = None, listen: list[str] | None = None) -> Callable:
    """
    A decorator that enables a function to participate in an event-driven system.

    - If `send` is provided, the function will emit the specified events after execution.
    - If `listen` is provided, the function will be registered as a listener for those events
      and executed when they are emitted.

    This allows seamless event propagation and reaction, making functions behave like observables.

    Args:
        send (Optional[List[str]]): A list of event names to emit after the function executes.
        listen (Optional[List[str]]): A list of event names the function should listen for.

    Returns:
        Callable: The decorated function with event-driven behavior.
    """

    def decorator(func: Callable) -> Callable:
        """Wraps the function to handle event subscription and emission."""

        async def register() -> None:
            """Registers the function as a listener if `listen` events are specified."""
            if listen:
                for event in listen:
                    await EventDispatcher.subscribe(event, func)

        # Use the portal to run the registration in a blocking manner
        with start_blocking_portal() as portal:
            portal.call(register)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Executes the function and emits events if specified.

            - If the function is asynchronous, it is awaited.
            - If the function is synchronous, it is executed in a separate thread.
            - After execution, events defined in `send` are emitted.

            Args:
                *args (Any): Positional arguments for the function.
                **kwargs (Any): Keyword arguments for the function.

            Returns:
                Any: The result of the function execution.
            """
            if is_async_callable(func):
                result = await func(*args, **kwargs)
            else:
                result = await anyio.to_thread.run_sync(func, *args, **kwargs)

            # Emit events after execution
            if send:
                async with anyio.create_task_group() as tg:
                    for event in send:
                        tg.start_soon(
                            lambda e=event, a=args, k=kwargs: EventDispatcher.emit(e, *a, **k)
                        )

            return result

        return wrapper

    return decorator
