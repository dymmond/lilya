from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.conf import settings
from lilya.contrib.schedulers.asyncz.config import AsynczConfig


# Declare your settings here.
# This is an example of how you can configure the Asyncz scheduler.
# You can customize the tasks, stores, executors, and other configurations as needed.
class AppSettings(Settings):

    @property
    def scheduler_config(self) -> AsynczConfig:
        return AsynczConfig(
            tasks=...,
            configurations={
                "asyncz.stores.mongo": {"type": "mongodb"},
                "asyncz.stores.default": {"type": "redis", "database": "0"},
                "asyncz.executors.threadpool": {
                    "max_workers": "20",
                    "class": "asyncz.executors.threadpool:ThreadPoolExecutor",
                },
                "asyncz.executors.default": {"class": "asyncz.executors.asyncio::AsyncIOExecutor"},
                "asyncz.task_defaults.coalesce": "false",
                "asyncz.task_defaults.max_instances": "3",
                "asyncz.task_defaults.timezone": "UTC",
            },
        )


# Create an instance of the Lilya application with the settings.
# This in theory is in a different file, but for the sake of this example, we are defining it here.
app = Lilya(
    on_startup=[settings.scheduler_config.start],
    on_shutdown=[settings.scheduler_config.shutdown],
)