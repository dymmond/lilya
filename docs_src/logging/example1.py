import sys

from typing import Any
import loguru

from lilya.apps import Lilya
from lilya.logging import LoggingConfig


class LoguruConfig(LoggingConfig):
    def __init__(self, level: str, **kwargs):
        super().__init__(level=level, **kwargs)

    def configure(self):
        loguru.logger.remove()
        loguru.logger.add(
            sink=sys.stdout,
            level=self.level,
            format="{time} {level} {message}",
            colorize=True,
        )

    def get_logger(self) -> Any:
        return loguru.logger


logging_config = LoguruConfig(level="INFO")

app = Lilya(logging_config=logging_config)
