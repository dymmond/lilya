import sys

from typing import Any
import orjson

from lilya.apps import Lilya
from lilya.serializers import SerializerConfig


class ORJSONConfig(SerializerConfig):
    def __init__(self, level: str, **kwargs):
        super().__init__(level=level, **kwargs)

    def get_serializer(self) -> Any:
        return orjson


serializer_config = ORJSONConfig()

app = Lilya(serializer_config=serializer_config)
