from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property

from edgy import Registry

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
    def registry(self) -> Registry:
        return Registry(TEST_DATABASE_URL)
