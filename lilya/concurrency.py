import functools
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator, TypeVar

import anyio.to_thread

from lilya.compat import is_async_callable

T = TypeVar("T")


async def run_in_threadpool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a callable in a threapool.
    Make sure the callable is always async.
    """
    def_func = AsyncCallable(func)
    return await def_func(*args, *kwargs)


def enforce_async_callable(func: Callable[..., Any]) -> Callable[..., Awaitable[T]]:
    """
    Enforces the callable to be async by returning an AsyncCallable.
    """
    return func if is_async_callable(func) else AsyncCallable(func)  # type:ignore


class AsyncCallable:
    """
    Creates an async callable and when called, runs in a threapool.
    """

    def __init__(self, func: Callable[..., Any], **kwargs: Any) -> None:
        self._callable = func
        self.kwargs = kwargs

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[T]:
        values = kwargs if not self.kwargs else self.kwargs
        return anyio.to_thread.run_sync(functools.partial(self._callable, **values), *args)

    async def run_in_threadpool(self, *args: Any, **kwargs: Any) -> T:
        return await self(*args, **kwargs)


class IterationStop(Exception):
    ...


def _next(iterator: Iterator[T]) -> T:
    try:
        return next(iterator)
    except StopIteration:
        raise IterationStop from None


async def iterate_in_threadpool(
    iterator: Iterator[T],
) -> AsyncIterator[T]:
    while True:
        try:
            yield await anyio.to_thread.run_sync(_next, iterator)
        except IterationStop:
            break
