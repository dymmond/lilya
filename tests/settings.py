from dataclasses import dataclass

from lilya.conf.enums import EnvironmentType
from lilya.conf.global_settings import Settings


@dataclass
class TestSettings(Settings):
    debug: bool = True
    environment: str = EnvironmentType.TESTING.value
