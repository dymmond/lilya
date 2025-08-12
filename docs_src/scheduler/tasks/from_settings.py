from lilya.apps import Lilya
from lilya.conf.global_settings import Settings
from lilya.conf import settings
from esmerald.contrib.schedulers.asyncz.config import AsynczConfig


# This is an example of how to configure tasks using the Asyncz scheduler in Lilya.
class AppSettings(Settings):
    enable_scheduler: bool = True

    @property
    def scheduler_config(self) -> AsynczConfig:
        return AsynczConfig(
            tasks={
                "collect_market_data": "accounts.tasks",
                "send_newsletter": "accounts.tasks",
            },
            stores=...,
            executors=...,
        )


# In theory, this is in a different file, but for the sake of this example, we are defining it here.
app = Lilya(
    routes=[...],
    on_startup=[settings.scheduler_config.start],
    on_shutdown=[settings.scheduler_config.shutdown],
)