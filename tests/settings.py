from __future__ import annotations

import os
from functools import cached_property

import orjson
from edgy import Registry

from lilya.conf.enums import EnvironmentType
from lilya.conf.global_settings import Settings
from lilya.serializers import SerializerConfig

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URI", "postgresql+asyncpg://postgres:postgres@localhost:5432/lilya"
)


class ORJSONSerializerConfig(SerializerConfig):
    def get_serializer(self):
        return orjson


class TestSettings(Settings):
    debug: bool = True
    environment: str = EnvironmentType.TESTING.value

    @cached_property
    def registry(self) -> Registry:
        return Registry(TEST_DATABASE_URL)

    @property
    def serializer_config(self) -> SerializerConfig:
        return ORJSONSerializerConfig()
