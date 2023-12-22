import sys

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from typing import Any, Callable, Sequence, Union

import anyio

from lilya._internal import Repr
from lilya.concurrency import enforce_async_callable

P = ParamSpec("P")


class Task(Repr):
    """
    The representation of a background task.
    """

    __slots__ = ("func", "args", "kwargs")

    def __init__(self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
        self.func = enforce_async_callable(func)
        self.args = args
        self.kwargs = kwargs

    async def __call__(self) -> None:
        await self.func(*self.args, **self.kwargs)


class Tasks(Task):
    """
    A container for background tasks.

    When `as_group` is set to True, it will run all the tasks
    concurrently (as a group)
    """

    __slots__ = ("tasks", "as_group")

    def __init__(self, tasks: Union[Sequence[Task], None] = None, as_group: bool = False):
        self.tasks = list(tasks) if tasks else []
        self.as_group = as_group

    def add_task(self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
        task = Task(func, *args, **kwargs)
        self.tasks.append(task)

    async def run_single(self) -> None:
        for task in self.tasks:
            await task()

    async def run_as_group(self) -> None:
        async with anyio.create_task_group() as group:
            for task in self.tasks:
                group.start_soon(task)

    async def __call__(self) -> None:
        if not self.as_group:
            await self.run_single()
        else:
            await self.run_as_group()
