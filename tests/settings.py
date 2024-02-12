from dataclasses import dataclass
from functools import cached_property
from typing import Tuple

from edgy import Database, Registry

from lilya.conf.enums import EnvironmentType
from lilya.conf.global_settings import Settings


@dataclass
class TestSettings(Settings):
    debug: bool = True
    environment: str = EnvironmentType.TESTING.value

    @cached_property
    def registry(self) -> Tuple[Database, Registry]:
        database = Database("postgresql+asyncpg://postgres:postgres@localhost:5432/lilya")
        return database, Registry(database=database)
