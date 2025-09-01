from typing import Any

import ujson

from lilya.serializers import SerializerConfig


class CustomSerializerConfig(SerializerConfig):
    def __init__(self, level: str, **kwargs):
        super().__init__(level=level, **kwargs)
        self.options = kwargs

    def get_serializer(self) -> Any:
        """
        Returns the serializer instance.
        """
        return ujson
