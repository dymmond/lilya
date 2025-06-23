from lilya.apps import Lilya
from lilya.routing import Include, Path
from lilya.dependencies import Provide, Provides

class FeatureFlagClient:
    def __init__(self, env):
        self.env = env
    async def is_enabled(self, flag):
        ...

# App-wide
app = Lilya()

# Mount an admin module with its own flags
admin_flags = lambda: FeatureFlagClient(env="admin")
public_flags = lambda: FeatureFlagClient(env="public")

app.include(
    path="/admin",
    app=Include(
        path="",
        routes=[
            Path(
                "/dashboard",
                handler=lambda flags=Provides(): flags.is_enabled("new_ui") and { ... }
            )
        ],
        dependencies={"flags": Provide(admin_flags)}
    )
)

app.include(
    path="/public",
    app=Include(
        path="",
        routes=[
            Path(
                "/home",
                handler=lambda flags=Provides(): flags.is_enabled("beta_banner")
            )
        ],
        dependencies={"flags": Provide(public_flags)}
    )
)
