from dataclasses import dataclass

from lilya.conf import Settings


@dataclass
class AppSettings(Settings):
    debug: bool = False
