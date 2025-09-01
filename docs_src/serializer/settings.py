from lilya.conf import Settings
from lilya.serializers import SerializerConfig

from myapp.serializers import ORJSONConfig


class CustomSettings(Settings):
    @property
    def serializer_config(self) -> SerializerConfig:
        return ORJSONConfig()
