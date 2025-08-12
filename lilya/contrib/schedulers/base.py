from typing import Any

from lilya.contrib.schedulers.protocols import SchedulerProtocol


class SchedulerConfig(SchedulerProtocol):
    def __init__(self, **kwargs: dict[str, Any]):
        super().__init__(**kwargs)

    async def start(self, **kwargs: dict[str, Any]) -> None:
        raise NotImplementedError("Every scheduler must implement the start method.")

    async def stop(self, **kwargs: dict[str, Any]) -> None:
        raise NotImplementedError("Every scheduler must implement the stop method.")
