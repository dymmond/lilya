from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides

app = Lilya(
    dependencies={"experiment_group": Provide(lambda: "control")}
)

# Override for this route only
@app.get("/landing", dependencies={"experiment_group": Provide(lambda: "variant")})
async def landing(exp=Provides()):
    if exp == "variant":
        return {"ui": "new"}
    return {"ui": "old"}
