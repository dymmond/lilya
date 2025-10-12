from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

# Define the type alias for a lifecycle hook: a callable that takes no arguments
# and returns either Any (for sync functions) or Awaitable[Any] (for async functions).
Hook = Callable[[], Any] | Callable[[], Awaitable[Any]]


class LifecycleRegistry:
    """
    A centralized, global registry for storing startup and shutdown hooks (callbacks).

    Lilya's application logic retrieves hooks from this registry and injects them
    into the ASGI lifespan protocol managed by the Router or Application instance.
    """

    __slots__ = ("startup", "shutdown", "_cleared")

    def __init__(self) -> None:
        """
        Initializes the registry with empty lists for startup and shutdown hooks.
        """
        self.startup: list[Hook] = []
        self.shutdown: list[Hook] = []
        self._cleared: bool = False

    def on_startup(self, func: Hook) -> Hook:
        """
        Registers a function to be executed when the application starts up.

        The hook function can be synchronous or asynchronous.

        Args:
            func: The callable (Hook) to register. It should take no arguments.

        Returns:
            The registered callable (`func`), allowing the method to be used as a decorator.
        """
        self.startup.append(func)
        return func

    def on_shutdown(self, func: Hook) -> Hook:
        """
        Registers a function to be executed when the application shuts down.

        The hook function can be synchronous or asynchronous.

        Args:
            func: The callable (Hook) to register. It should take no arguments.

        Returns:
            The registered callable (`func`), allowing the method to be used as a decorator.
        """
        self.shutdown.append(func)
        return func

    def get_hooks(self) -> dict[str, list[Hook]]:
        """
        Retrieves copies of the currently registered startup and shutdown hooks.

        Returns:
            A dictionary containing two keys: "startup" and "shutdown", each mapping
            to a new list containing the registered `Hook` callables. Returning copies
            prevents external modification of the registry's internal lists.
        """
        return {"startup": list(self.startup), "shutdown": list(self.shutdown)}

    def clear(self) -> None:
        """
        Clears all registered startup and shutdown hooks.

        This method is primarily intended for isolating tests.
        Sets the internal `_cleared` flag to True.
        """
        self.startup.clear()
        self.shutdown.clear()
        self._cleared = True


# Global instance of the lifecycle registry.
_registry: LifecycleRegistry = LifecycleRegistry()


def on_startup(func: Hook) -> Hook:
    """
    Decorator to register a global startup hook.

    Registers a synchronous or asynchronous function to run during the application's
    ASGI lifespan startup phase.

    Args:
        func: The hook function to register. Must accept no arguments.

    Returns:
        The decorated function.

    Example:
        ```python
        from lilya.lifecycle import on_startup

        @on_startup
        async def connect_db():
            # Code to run before the application can receive requests
            await db.connect()
        ```
    """
    return _registry.on_startup(func)


def on_shutdown(func: Hook) -> Hook:
    """
    Decorator to register a global shutdown hook.

    Registers a synchronous or asynchronous function to run during the application's
    ASGI lifespan shutdown phase.

    Args:
        func: The hook function to register. Must accept no arguments.

    Returns:
        The decorated function.

    Example:
        ```python
        from lilya.lifecycle import on_shutdown

        @on_shutdown
        async def disconnect_db():
            # Code to run after the application stops receiving requests
            await db.close()
        ```
    """
    return _registry.on_shutdown(func)


def get_hooks() -> dict[str, list[Hook]]:
    """
    Retrieves copies of all globally registered startup and shutdown hooks.

    This function delegates the call to the global `LifecycleRegistry` instance.

    Returns:
        A dictionary with "startup" and "shutdown" keys, mapping to lists of `Hook` callables.
    """
    return _registry.get_hooks()


async def run_hooks(hooks: list[Hook]) -> None:
    """
    Sequentially executes a list of lifecycle hooks.

    Supports both synchronous and asynchronous hook functions. If a hook returns an
    awaitable object (e.g., a coroutine), it is awaited before proceeding to the next hook.

    Args:
        hooks: A list of `Hook` callables to be executed.
    """
    for hook in hooks:
        result: Any = hook()

        # Check if the result is a coroutine or other awaitable (like futures)
        if inspect.isawaitable(result):
            await result


def _clear_for_tests_only() -> None:  # pragma: no cover
    """
    Clears all registered startup and shutdown hooks in the global registry.

    This function is intended strictly for use within testing environments
    to ensure hook registration does not leak between tests.
    """
    _registry.clear()
