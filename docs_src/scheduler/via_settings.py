from asyncz.executors import AsyncIOExecutor, ThreadPoolExecutor
from asyncz.stores.mongo import MongoDBStore
from lilya.conf.global_settings import Settings
from lilya.contrib.schedulers.base import SchedulerConfig
from lilya.contrib.schedulers.asyncz.config import AsynczConfig


class CustomSettings(Settings):

    @property
    def scheduler_config(self) -> SchedulerConfig:
        stores = {"default": MongoDBStore()}

        # Define the executors
        # Override the default ot be the AsyncIOExecutor
        executors = {
            "default": AsyncIOExecutor(),
            "threadpool": ThreadPoolExecutor(max_workers=20),
        }

        # Set the defaults
        task_defaults = {"coalesce": False, "max_instances": 4}

        return AsynczConfig(
            tasks=...,
            timezone="UTC",
            stores=stores,
            executors=executors,
            task_defaults=task_defaults,
        )