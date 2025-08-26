from __future__ import annotations

import hashlib
import inspect
import json
import re
import threading
from collections.abc import Callable
from functools import wraps
from typing import Any

import anyio
from anyio.from_thread import start_blocking_portal

from lilya._internal._encoders import json_encode
from lilya._internal._events import EventDispatcher  # noqa
from lilya.compat import is_async_callable
from lilya.conf import _monkay
from lilya.logging import logger
from lilya.protocols.cache import CacheBackend


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


def generate_cache_key(func: Callable, args: Any, kwargs: Any) -> str:
    """
    Generates a stable cache key ensuring it does not include `<locals>`.
    """
    # Get module and function name
    key_base = f"{func.__module__}.{func.__qualname__}"

    # Ensure that nested function names do not include <locals>
    key_base = re.sub(r"\.<locals>\.", ".", key_base)

    # Convert args & kwargs into a deterministic format
    def convert(value: Any) -> Any:
        if isinstance(value, tuple):
            return list(value)  # Convert tuples to lists
        if isinstance(value, set):
            return sorted(value)  # Convert sets to sorted lists for consistency
        return value

    try:
        bound_method = inspect.ismethod(func) or (
            len(args) > 0 and hasattr(args[0], func.__name__)
        )
    except Exception:  # noqa
        bound_method = False

    args_to_encode = args[1:] if bound_method else args

    serialized_data = json.dumps(
        {
            "args": [convert(json_encode(arg)) for arg in args_to_encode],
            "kwargs": {k: convert(json_encode(v)) for k, v in kwargs.items()},
        },
    )

    # Use a stable hash to ensure key format remains consistent
    key_hash = hashlib.md5(serialized_data.encode("utf-8")).hexdigest()

    return f"{key_base}:{key_hash}"


# Lock for thread safety
cache_lock = threading.Lock()


class cache:  # noqa
    """
    A function-based caching decorator with TTL support, cache invalidation, and flexible backends.

    This decorator works with both **synchronous** and **asynchronous** functions, supporting AnyIO-based
    thread safety for cache operations. It prevents repeated expensive computations by caching the result
    of function calls and returning cached values when available.

    If the cache backend fails, the function executes normally, and errors are logged without
    affecting the function's behavior.

    Args:
        ttl (Optional[int]): Time-to-live (TTL) in seconds for cached entries.
            - If `None`, the cache entry never expires.
        backend (Optional[CacheBackend]): Custom cache backend to store the data.
            - Defaults to `settings.cache_backend` if not provided.

    Example:
        >>> @cache(ttl=10)
        >>> async def get_data():
        >>>     return "expensive_computation"
    """

    def __init__(self, ttl: int | None = None, backend: CacheBackend | None = None) -> None:
        """
        Initializes the caching decorator with optional TTL and a cache backend.

        Args:
            ttl (Optional[int]): Time in seconds before a cache entry expires.
            backend (Optional[CacheBackend]): The cache backend implementation.
        """
        self.ttl = ttl or _monkay.settings.cache_default_ttl
        self.backend = backend or _monkay.settings.cache_backend

    def __call__(self, func: Callable) -> Any:
        """
        Wraps a function with caching logic to store and retrieve results from cache.

        This method determines whether the function is **synchronous** or **asynchronous**
        and applies the appropriate caching mechanism.

        - **For async functions**, it awaits the result and caches it.
        - **For sync functions**, it uses `anyio.run()` to interact with the async cache backend.

        If a cache backend failure occurs, the function runs as usual, and the error is logged.

        Args:
            func (Callable): The function to be decorated.

        Returns:
            Callable: A wrapped function that integrates caching.
        """
        if is_async_callable(func):  # Handle async functions

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """
                Asynchronous cache wrapper.

                Attempts to retrieve the cached value before calling the actual function.
                If the cache fails, it logs the error and continues execution.

                Args:
                    *args: Positional arguments for the decorated function.
                    **kwargs: Keyword arguments for the decorated function.

                Returns:
                    Any: The cached value if available, otherwise the function result.
                """
                key = generate_cache_key(func, args, kwargs)

                async with anyio.Lock():  # Ensure async thread safety
                    try:
                        cached_value = await self.backend.get(key)
                        if cached_value is not None:
                            return cached_value
                    except Exception as e:
                        logger.error(f"Cache backend failure in get(): {e}", exc_info=True)

                    # Proceed with function execution if cache fails
                    result = await func(*args, **kwargs)

                    try:
                        await self.backend.set(key, result, self.ttl)
                    except Exception as e:
                        logger.error(f"Cache backend failure in set(): {e}", exc_info=True)

                    return result

            return async_wrapper

        else:  # Handle sync functions with AnyIO for thread safety

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                """
                Synchronous cache wrapper.

                Uses `anyio.run()` to interact with the async cache backend safely.

                Args:
                    *args: Positional arguments for the decorated function.
                    **kwargs: Keyword arguments for the decorated function.

                Returns:
                    Any: The cached value if available, otherwise the function result.
                """
                key = generate_cache_key(func, args, kwargs)

                with cache_lock:  # Ensure sync thread safety
                    try:

                        async def get_cached() -> Any:
                            """Retrieve a cached value asynchronously inside a sync function."""
                            return await self.backend.get(key)

                        cached_value = anyio.run(get_cached)

                        if cached_value is not None:
                            return cached_value
                    except Exception as e:
                        logger.error(f"Cache backend failure in get(): {e}", exc_info=True)

                    # Proceed with function execution if cache fails
                    result = func(*args, **kwargs)

                    try:

                        async def set_cache() -> None:
                            """Store a computed value asynchronously inside a sync function."""
                            await self.backend.set(key, result, self.ttl)

                        anyio.run(set_cache)
                    except Exception as e:
                        logger.error(f"Cache backend failure in set(): {e}", exc_info=True)

                    return result

            return sync_wrapper

    def invalidate(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """
        Invalidates the cache entry for a specific function call with given arguments.

        This removes the cached value for a particular function signature, ensuring
        fresh execution the next time it is called.

        Args:
            func (Callable): The decorated function whose cache entry should be invalidated.
            *args: Positional arguments used to generate the cache key.
            **kwargs: Keyword arguments used to generate the cache key.

        Example:
            >>> @cache(ttl=30)
            >>> async def get_user_data(user_id: int):
            >>>     return fetch_from_db(user_id)

            >>> cache.invalidate(get_user_data, user_id=42)  # Removes cache for user 42
        """
        key = generate_cache_key(func, args, kwargs)

        with cache_lock:  # Prevent multiple threads from invalidating at the same time
            try:

                async def delete_cache() -> None:
                    """Delete a cache entry asynchronously."""
                    await self.backend.delete(key)

                anyio.run(delete_cache)
            except Exception as e:
                logger.error(f"Cache backend failure in delete(): {e}", exc_info=True)
