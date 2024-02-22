import os
from dataclasses import dataclass
from functools import cached_property
from typing import Tuple

from edgy import Database, Registry

from lilya.conf.enums import EnvironmentType
from lilya.conf.global_settings import Settings

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URI", "postgresql+asyncpg://postgres:postgres@localhost:5432/lilya"
)


@dataclass
class TestSettings(Settings):
    debug: bool = True
    environment: str = EnvironmentType.TESTING.value

    @cached_property
    def registry(self) -> Tuple[Database, Registry]:
        database = Database(TEST_DATABASE_URL)
        return database, Registry(database=database)
