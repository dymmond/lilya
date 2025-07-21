from lilya.apps import Lilya
from lilya.conf.global_settings import Settings


class LilyaSettings(Settings):
    debug: bool = False
    secret_key: str = "a child secret"


app = Lilya(
    routes=...,
    settings_module=LilyaSettings,
)
