from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.enums import Scope
from myapp.config import GlobalConfig

config = GlobalConfig.load()

app = Lilya(
    dependencies={
        "config": Provide(lambda: config, scope=Scope.GLOBAL, use_cache=True)
    }
)

@app.get("/info")
async def get_info(config=Provides()):
    return {"env": config.env, "version": config.version}
