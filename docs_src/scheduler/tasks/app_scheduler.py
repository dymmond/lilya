from lilya.apps import Lilya
from lilya.contrib.schedulers.asyncz.config import AsynczConfig

scheduler_config=AsynczConfig(
    tasks={
        "collect_market_data": "accounts.tasks",
        "send_newsletter": "accounts.tasks",
    },
),

app = Lilya(
    routes=[...],
    on_startup=[scheduler_config.start],
    on_shutdown=[scheduler_config.shutdown],
)