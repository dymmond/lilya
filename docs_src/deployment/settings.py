from dataclasses import dataclass

from lilya.conf.global_settings import Settings


@dataclass
class AppSettings(Settings):
    debug: bool = False
