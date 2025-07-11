import functools
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from typing import Any, TypeVar

import anyio.to_thread
from anyio import create_task_group, get_cancelled_exc_class, to_thread

from lilya.compat import is_async_callable

T = TypeVar("T")


async def run_in_threadpool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a callable in a threadpool.
    Make sure the callable is always async.
    """
    def_func = AsyncCallable(func)
    return await def_func(*args, **kwargs)


def enforce_async_callable(func: Callable[..., Any]) -> Callable[..., Awaitable[T]]:
    """
    Enforces the callable to be async by returning an AsyncCallable.
    """
    return func if is_async_callable(func) else AsyncCallable(func)


class AsyncCallable:
    """
    Creates an async callable and when called, runs in a thread pool.
    """

    __slots__ = ("_callable", "default_kwargs")

    def __init__(self, func: Callable[..., Any], **kwargs: Any) -> None:
        self._callable = func
        self.default_kwargs = kwargs

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[T]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        return anyio.to_thread.run_sync(
            functools.partial(self._callable, *args, **combined_kwargs)
        )

    async def run_in_threadpool(self, *args: Any, **kwargs: Any) -> T:
        return await self(*args, **kwargs)


async def iterate_in_threadpool(iterator: Iterable[T]) -> AsyncIterator[T]:
    async def worker() -> AsyncIterator[T]:
        for item in iterator:
            yield item

    async with create_task_group():
        stream = await to_thread.run_sync(worker)
        try:
            async for item in stream:
                yield item
        except get_cancelled_exc_class():
            ...
