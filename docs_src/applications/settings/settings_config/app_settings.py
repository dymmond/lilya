from dataclasses import dataclass

from lilya.conf import Settings


@dataclass
class InstanceSettings(Settings):
    debug: bool = False
