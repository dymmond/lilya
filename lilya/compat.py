from __future__ import annotations

import asyncio
import functools
import hashlib
from concurrent import futures
from concurrent.futures import Future
from typing import Any, Awaitable, Generator, Generic, Protocol, TypeVar

from lilya._internal._urls import reverse as reverse

T = TypeVar("T")


class SupportsAsyncClose(Protocol):
    async def close(self) -> None: ...  # pragma: no cover


SupportsAsyncCloseType = TypeVar(
    "SupportsAsyncCloseType", bound=SupportsAsyncClose, covariant=False
)


try:
    hashlib.md5(b"data", usedforsecurity=False)  # type: ignore[call-arg]

    def md5_hexdigest(data: bytes, *, usedforsecurity: bool = True) -> str:  # pragma: no cover
        return hashlib.md5(  # type: ignore[call-arg]
            data, usedforsecurity=usedforsecurity
        ).hexdigest()

except TypeError:  # pragma: no cover

    def md5_hexdigest(data: bytes, *, usedforsecurity: bool = True) -> str:
        return hashlib.md5(data).hexdigest()


def is_async_callable(obj: Any) -> bool:
    """
    Validates if a given object is an async callable or not.
    """
    while isinstance(obj, functools.partial):
        obj = obj.func

    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(obj.__call__)
    )


def run_sync(async_function: Awaitable) -> Any:
    """
    Runs the queries in sync mode
    """
    try:
        return asyncio.run(async_function)  # type: ignore
    except RuntimeError:
        with futures.ThreadPoolExecutor(max_workers=1) as executor:
            future: Future = executor.submit(asyncio.run, async_function)  # type: ignore
            return future.result()


class AsyncResourceHandler(Generic[SupportsAsyncCloseType]):
    """
    An asynchronous resource handler that acts as either an awaitable or a context manager.
    """

    __slots__ = ("awaitable_resource", "entered_resource")

    def __init__(self, awaitable_resource: Awaitable[SupportsAsyncCloseType]) -> None:
        """
        Initialize the AsyncResourceHandler with the provided awaitable resource.

        Args:
            awaitable_resource (Awaitable[SupportsAsyncCloseType]): The awaitable resource.
        """
        self.awaitable_resource = awaitable_resource

    def __await__(self) -> Generator[Any, None, SupportsAsyncCloseType]:
        """
        Allow the instance to be used as an awaitable.

        Returns:
            Generator[Any, None, SupportsAsyncCloseType]: The awaited resource.
        """
        return self.awaitable_resource.__await__()

    async def __aenter__(self) -> SupportsAsyncCloseType:
        """
        Enter the asynchronous context and obtain the resource.

        Returns:
            SupportsAsyncCloseType: The obtained resource.
        """
        self.entered_resource = await self.awaitable_resource
        return self.entered_resource

    async def __aexit__(self, *args: Any) -> None | bool:
        """
        Exit the asynchronous context and close the resource.

        Args:
            *args: Additional arguments.

        Returns:
            Union[None, bool]: Returns None or a boolean value indicating the exit status.
        """
        await self.entered_resource.close()
        return None
