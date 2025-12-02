from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from asyncz.executors.base import BaseExecutor
from asyncz.schedulers import AsyncIOScheduler
from asyncz.schedulers.base import BaseScheduler, default_loggers_class
from asyncz.schedulers.datastructures import TaskDefaultStruct
from asyncz.stores.base import BaseStore
from asyncz.tasks.types import TaskType
from asyncz.triggers import IntervalTrigger
from asyncz.triggers.base import BaseTrigger
from loguru import logger

from lilya.apps import Lilya
from lilya.contrib.schedulers.asyncz.config import AsynczConfig
from lilya.contrib.schedulers.asyncz.decorator import scheduler
from lilya.exceptions import ImproperlyConfigured


class DummyScheduler(BaseScheduler):  # pragma: no cover
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wakeup = MagicMock()

    def shutdown(self, wait=True):
        super().shutdown(wait)

    def wakeup(self): ...


class DummyTrigger(BaseTrigger):  # pragma: no cover
    def __init__(self, **args):
        super().__init__(**args)
        self.args = args

    def get_next_trigger_time(
        self, previous_time: datetime, now: datetime | None = None
    ) -> datetime | None: ...


class DummyExecutor(BaseExecutor):  # pragma: no cover
    def __init__(self, **args):
        super().__init__(**args)
        self.args = args
        self.start = MagicMock()
        self.shutdown = MagicMock()
        self.send_task = MagicMock()

    def do_send_task(self, task: "TaskType", run_times: list[datetime]) -> Any:
        return super().do_send_task(task, run_times)


class DummyStore(BaseStore):  # pragma: no cover
    def __init__(self, **args):
        super().__init__(**args)
        self.args = args
        self.start = MagicMock()
        self.shutdown = MagicMock()

    def get_due_tasks(self, now: datetime) -> list["TaskType"]: ...

    def lookup_task(self, task_id: str | int) -> "TaskType": ...

    def delete_task(self, task_id: str | int): ...

    def remove_all_tasks(self): ...

    def get_next_run_time(self) -> datetime: ...

    def get_all_tasks(self) -> list["TaskType"]: ...

    def add_task(self, task: "TaskType"): ...

    def update_task(self, task: "TaskType"): ...


def scheduler_tasks() -> dict[str, str]:
    return {
        "task_one": "tests.contrib.schedulers.asyncz.test_scheduler",
        "task_two": "tests.contrib.schedulers.asyncz.test_scheduler",
    }


@scheduler(name="task1", trigger=IntervalTrigger(seconds=1), max_instances=3, is_enabled=True)
def task_one():  # pragma: no cover
    value = 3
    logger.info(value)
    return 3


@scheduler(name="task2", trigger=IntervalTrigger(seconds=3), max_instances=3, is_enabled=True)
def task_two():  # pragma: no cover
    value = 8
    logger.info(value)
    return 8


scheduler_config = AsynczConfig(tasks=scheduler_tasks())


def test_access_original_function() -> None:
    assert task_one.original.__name__ == "task_one"
    assert task_two.original.__name__ == "task_two"


def test_lilya_starts_scheduler():
    Lilya(
        on_startup=[scheduler_config.start],
        on_shutdown=[scheduler_config.shutdown],
    )
    assert scheduler_config.tasks == scheduler_tasks()
    assert scheduler_config.scheduler_class == AsyncIOScheduler


@pytest.fixture
def scheduler_class(monkeypatch):
    scheduler_class = AsyncIOScheduler
    scheduler_class._setup = MagicMock()
    # by patching out _setup task_defaults are not initialized anymore
    scheduler_class.task_defaults = TaskDefaultStruct()
    scheduler_class.timezone = timezone.utc
    scheduler_class.loggers = default_loggers_class()
    scheduler_class.logger_name = "asyncz.schedulers"
    return scheduler_class


@pytest.mark.parametrize(
    "global_config",
    [
        {
            "asyncz.timezone": "UTC",
            "asyncz.task_defaults.mistrigger_grace_time": "5",
            "asyncz.task_defaults.coalesce": "false",
            "asyncz.task_defaults.max_instances": "9",
            "asyncz.executors.default.class": f"{__name__}:DummyExecutor",
            "asyncz.executors.default.arg1": "3",
            "asyncz.executors.default.arg2": "a",
            "asyncz.executors.alter.class": f"{__name__}:DummyExecutor",
            "asyncz.executors.alter.arg": "true",
            "asyncz.stores.default.class": f"{__name__}:DummyStore",
            "asyncz.stores.default.arg1": "3",
            "asyncz.stores.default.arg2": "a",
            "asyncz.stores.bar.class": f"{__name__}:DummyStore",
            "asyncz.stores.bar.arg": "false",
        },
        {
            "asyncz.timezone": "UTC",
            "asyncz.task_defaults": {
                "mistrigger_grace_time": "5",
                "coalesce": "false",
                "max_instances": "9",
            },
            "asyncz.executors": {
                "default": {"class": f"{__name__}:DummyExecutor", "arg1": "3", "arg2": "a"},
                "alter": {"class": f"{__name__}:DummyExecutor", "arg": "true"},
            },
            "asyncz.stores": {
                "default": {"class": f"{__name__}:DummyStore", "arg1": "3", "arg2": "a"},
                "bar": {"class": f"{__name__}:DummyStore", "arg": "false"},
            },
        },
    ],
    ids=["ini-style", "yaml-style"],
)
def test_lilya_scheduler_configurations(scheduler_class, global_config):
    scheduler_config = AsynczConfig(
        tasks=scheduler_tasks(), scheduler_class=scheduler_class, configurations=global_config
    )
    Lilya(
        on_startup=[scheduler_config.start],
        on_shutdown=[scheduler_config.shutdown],
    )

    scheduler_config.scheduler_class._setup.assert_called_once_with(
        {
            "timezone": "UTC",
            "task_defaults": {
                "mistrigger_grace_time": "5",
                "coalesce": "false",
                "max_instances": "9",
            },
            "executors": {
                "default": {"class": f"{__name__}:DummyExecutor", "arg1": "3", "arg2": "a"},
                "alter": {"class": f"{__name__}:DummyExecutor", "arg": "true"},
            },
            "stores": {
                "default": {"class": f"{__name__}:DummyStore", "arg1": "3", "arg2": "a"},
                "bar": {"class": f"{__name__}:DummyStore", "arg": "false"},
            },
        }
    )


def test_raise_exception_on_tasks_key(scheduler_class):
    """
    Raises Esmerald ImproperlyConfigured if task passed has not a format dict[str, str]
    """
    tasks = {
        1: "tests.contrib.schedulers.asyncz.test_scheduler",
        2: "tests.contrib.schedulers.asyncz.test_scheduler",
    }

    with pytest.raises(ImproperlyConfigured):
        scheduler_config = AsynczConfig(scheduler_class=scheduler_class, tasks=tasks)
        Lilya(
            on_startup=[scheduler_config.start],
            on_shutdown=[scheduler_config.shutdown],
        )


def test_raise_exception_on_tasks_value(scheduler_class):
    """
    Raises Esmerald ImproperlyConfigured if task passed has not a format dict[str, str]
    """
    tasks = {
        "task_one": 1,
        "task_two": 2,
    }

    with pytest.raises(ImproperlyConfigured):
        scheduler_config = AsynczConfig(scheduler_class=scheduler_class, tasks=tasks)
        Lilya(
            on_startup=[scheduler_config.start],
            on_shutdown=[scheduler_config.shutdown],
        )
