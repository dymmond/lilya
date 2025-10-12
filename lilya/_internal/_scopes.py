from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from lilya.enums import Scope

# Generic type variable for the dependency callable return type
T = TypeVar("T")
# Type alias for the cache key: (scope, the original dependency function)
ScopeKey = tuple[Scope, Callable[..., Any]]
# Type alias for cleanup callbacks, which take no arguments and can be sync or async
CleanupCallback = Callable[[], Any] | Callable[[], Awaitable[Any]]


class ScopeManager:
    """
    Central registry for managing dependency instances across different scopes
    (GLOBAL, APP, and REQUEST) within a Lilya application's dependency injection system.

    This manager is responsible for caching instances for non-REQUEST scopes (GLOBAL, APP)
    and executing cleanup routines upon application shutdown.
    """

    def __init__(self) -> None:
        """
        Initializes the ScopeManager with an empty cache for instances and a list
        for registered cleanup routines.

        Internal Attributes:
            _instances: Dictionary mapping a dependency's scope and callable key to its
                        resolved instance value.
            _cleanup_callbacks: List of sync or async callables to run during the
                                application's asynchronous close cycle (`aclose`).
            _cleared: Boolean flag (not explicitly used in the original code, but implied by class structure)
        """
        self._instances: dict[ScopeKey, Any] = {}
        self._cleanup_callbacks: list[CleanupCallback] = []

    async def get_or_create(
        self,
        scope: Scope,
        dependency: Callable[..., T],
        factory: Callable[[], Any],
    ) -> T:
        """
        Retrieves a dependency instance from the cache if it exists for the given scope,
        or creates a new instance using the factory callable.

        - **REQUEST scope:** Always creates a new instance (no caching).
        - **GLOBAL/APP scopes:** Caches the created instance for subsequent calls.

        Args:
            scope: The dependency's intended lifespan scope (`Scope.GLOBAL`, `Scope.APP`, or `Scope.REQUEST`).
            dependency: The original dependency function used as part of the unique cache key.
            factory: A callable (sync or async) that, when executed, produces the dependency instance.

        Returns:
            The resolved dependency instance (`T`).
        """
        key: ScopeKey = (scope, dependency)

        # For per-request dependencies (REQUEST scope), we never cache.
        if scope == Scope.REQUEST:
            return await self._call(factory)

        # For GLOBAL and APP scopes, check the cache.
        if key not in self._instances:
            # If not in cache, create the instance and store it.
            value = await self._call(factory)
            self._instances[key] = value

        return self._instances[key]  # type: ignore

    async def _call(self, fn: Callable[[], T | Awaitable[T]]) -> T:
        """
        Internal helper to execute a callable, handling both synchronous and asynchronous functions.

        Args:
            fn: The callable (factory or hook) to execute.

        Returns:
            The result of the callable.
        """
        # Check if the callable is an async function (a coroutine function)
        if inspect.iscoroutinefunction(fn):
            # The type hint on fn() is simplified here since it's already constrained by factory/Hook
            return await fn()  # type: ignore

        # Execute as a synchronous function
        return fn()  # type: ignore

    async def aclose(self) -> None:
        """
        Executes all registered cleanup callbacks and clears the instance cache.

        This method is designed to be called during the application's shutdown process (lifespan shutdown).
        It awaits asynchronous callbacks and suppresses any exceptions raised by the callbacks.
        """
        for fn in self._cleanup_callbacks:
            try:
                result: Any = fn()
                # Check if the result of the synchronous call is an awaitable (e.g., a coroutine object)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: E722
                # Suppress exceptions during cleanup to ensure all callbacks are attempted.
                ...
        self._instances.clear()
        self._cleanup_callbacks.clear()

    def clear(self, scope: Scope | None = None) -> None:
        """
        Clears cached dependency instances for a specific scope or all scopes.

        This is primarily used for resetting state, often in testing environments.

        Args:
            scope: Optional. The specific `Scope` whose instances should be cleared
                   (e.g., `Scope.APP`). If `None` (default), all cached instances
                   across all scopes are cleared.
        """
        if scope:
            # Find and delete keys matching the specified scope
            to_delete: list[ScopeKey] = [k for k in self._instances if k[0] == scope]
            for k in to_delete:
                del self._instances[k]
        else:
            # Clear all instances
            self._instances.clear()


# Global singleton manager instance used across the framework.
scope_manager: ScopeManager = ScopeManager()
