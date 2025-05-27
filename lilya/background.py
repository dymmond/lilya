from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, ParamSpec

import anyio

from lilya._internal import Repr
from lilya.concurrency import enforce_async_callable

P = ParamSpec("P")


class Task(Repr):
    """
    `Task` as a single instance can be easily achieved.

    **Example**

    ```python
    from datetime import datetime
    from typing import Dict

    from lilya.apps import Lilya
    from lilya.background import Task
    from lilya.requests import Request
    from lilya.responses import Response
    from lilya.routing import Path


    async def send_email_notification(email: str, message: str):
        send_notification(email, message)


    async def create_user(request: Request) -> Response(Dict[str, str]):
        return Response(
            {"message": "Email sent"},
            background=Task(
                send_email_notification,
                email="example@lilya.dev",
                message="Thank you for registering.",
            ),
        )


    app = Lilya(
        routes=[
            Path(
                "/register",
                create_user,
                methods=["POST"],
            )
        ]
    )
    ```
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

    When `as_group` is set to `True`, it will run all the tasks
    concurrently (as a group).

    **Example**

    ```python
    from datetime import datetime

    from lilya.apps import Lilya
    from lilya.background import Tasks
    from lilya.requests import Request
    from lilya.responses import Response
    from lilya.routing import Path


    async def send_email_notification(email: str, message: str):
        send_notification(email, message)


    def write_in_file(email: str):
        with open("log.txt", mode="w") as log:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = f"Notification sent @ {now} to: {email}"
            log.write(content)


    async def create_user(request: Request):
        background_tasks = Tasks(as_group=True)
        background_tasks.add_task(
            send_email_notification,
            email="example@lilya.dev",
            message="Thank you for registering.",
        )
        background_tasks.add_task(write_in_file, email=request.user.email)

        return Response({"message": "Email sent"}, background=background_tasks)


    app = Lilya(
        routes=[
            Path(
                "/register",
                create_user,
                methods=["POST"],
            )
        ]
    )
    ```
    """

    __slots__ = ("tasks", "as_group")

    def __init__(self, tasks: Sequence[Task] | None = None, as_group: bool = False):
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
