from dataclasses import dataclass

from lilya.app import Lilya
from lilya.conf import Settings


@dataclass
class LilyaSettings(Settings):
    debug: bool = False
    secret_key: str = "a child secret"


app = Lilya(
    routes=...,
    settings_module=LilyaSettings,
)
