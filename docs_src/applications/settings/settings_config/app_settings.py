from dataclasses import dataclass

from lilya.conf.global_settings import Settings


@dataclass
class InstanceSettings(Settings):
    debug: bool = False
