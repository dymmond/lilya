from __future__ import annotations

from typing import Callable

import pytest

from lilya.background import Task, Tasks
from lilya.responses import Response
from lilya.testclient import TestClient


class TaskException(Exception): ...


def test_async_task(test_client_factory):
    TASK_COMPLETE = False

    async def async_task():
        nonlocal TASK_COMPLETE
        TASK_COMPLETE = True

    task = Task(async_task)

    async def app(scope, receive, send):
        response = Response("Task started", media_type="text/plain", background=task)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "Task started"
    assert TASK_COMPLETE


def test_sync_task(test_client_factory):
    TASK_COMPLETE = False

    def sync_task():
        nonlocal TASK_COMPLETE
        TASK_COMPLETE = True

    task = Task(sync_task)

    async def app(scope, receive, send):
        response = Response("Task started", media_type="text/plain", background=task)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "Task started"
    assert TASK_COMPLETE


def test_multiple_tasks(test_client_factory: Callable[..., TestClient]):
    TASK_COUNTER = 0

    def increment(amount):
        nonlocal TASK_COUNTER
        TASK_COUNTER += amount

    async def app(scope, receive, send):
        tasks = Tasks()
        tasks.add_task(increment, amount=1)
        tasks.add_task(increment, amount=2)
        tasks.add_task(increment, amount=3)
        response = Response("Task started", media_type="text/plain", background=tasks)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "Task started"
    assert TASK_COUNTER == 1 + 2 + 3


def test_multi_tasks_failure_avoids_next_execution(
    test_client_factory: Callable[..., TestClient],
) -> None:
    TASK_COUNTER = 0

    def increment():
        nonlocal TASK_COUNTER
        TASK_COUNTER += 1
        if TASK_COUNTER == 1:
            raise TaskException("Task failed")

    async def app(scope, receive, send):
        tasks = Tasks()
        tasks.add_task(increment)
        tasks.add_task(increment)
        response = Response("Task started", media_type="text/plain", background=tasks)
        await response(scope, receive, send)

    client = test_client_factory(app)
    with pytest.raises(TaskException):  # noqa: B017
        client.get("/")

    assert TASK_COUNTER == 1


@pytest.mark.asyncio
async def test_background_tasks_as_group() -> None:
    values: set[str] = set()

    def set_values(values_to_add) -> None:
        for value in values_to_add:
            values.add(value)

    tasks = Tasks(
        [
            Task(set_values, ["a", "b", "c", "h"]),
            Task(set_values, values_to_add=["d", "e", "f", "g"]),
        ],
        as_group=True,
    )

    async def app(scope, receive, send):
        response = Response("Task started", media_type="text/plain", background=tasks)
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")

    assert response.text == "Task started"
    assert len(values) == 8
