from lilya.apps import ChildLilya, Lilya
from lilya.conf.global_settings import Settings
from lilya.routing import Include


class ChildLilyaSettings(Settings):
    debug: bool = True
    secret_key: str = "a child secret"


## Create a ChildLilya application
child_app = ChildLilya(
    routes=[...],
    settings_module=ChildLilyaSettings,
)

# Create a Lilya application
app = Lilya(
    routes=[
        Include("/child", app=child_app),
    ]
)
