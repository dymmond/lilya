import functools
from typing import Any, AsyncIterator, Callable, Iterator, TypeVar

import anyio.to_thread

T = TypeVar("T")


async def run_in_threadpool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    if kwargs:  # pragma: no cover
        # run_sync doesn't accept 'kwargs', so bind them in here
        func = functools.partial(func, **kwargs)
    return await anyio.to_thread.run_sync(func, *args)


class IterationStop(Exception):
    ...


def _next(iterator: Iterator[T]) -> T:
    try:
        return next(iterator)
    except StopIteration:
        raise IterationStop


async def iterate_in_threadpool(
    iterator: Iterator[T],
) -> AsyncIterator[T]:
    while True:
        try:
            yield await anyio.to_thread.run_sync(_next, iterator)
        except IterationStop:
            break
