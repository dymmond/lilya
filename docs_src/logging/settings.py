from lilya.conf import Settings
from lilya.logging import LoggingConfig

from myapp.logging import LoguruLoggingConfig


class CustomSettings(Settings):
    @property
    def logging_config(self) -> LoggingConfig:
        return LoguruLoggingConfig(level="DEBUG")
