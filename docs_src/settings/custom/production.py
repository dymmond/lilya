from __future__ import annotations

from dataclasses import dataclass

from lilya.types import LifespanEvent

from ..configs.base import AppSettings


async def start_database(): ...


async def close_database(): ...


@dataclass
class ProductionSettings(AppSettings):
    # the environment can be names to whatever you want.
    environment: bool = "production"
    debug: bool = True
    reload: bool = False

    @property
    def on_startup(self) -> list[LifespanEvent]:
        """
        List of events/actions to be done on_startup.
        """
        return [start_database]

    @property
    def on_shutdown(self) -> list[LifespanEvent]:
        """
        List of events/actions to be done on_shutdown.
        """
        return [close_database]
