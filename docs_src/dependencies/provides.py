from lilya.apps import Lilya
from lilya.dependencies import Provides

app = Lilya

@app.get("/charge")
async def charge_customer(api_key=Provides()):
    # `api_key` is resolved via your Provide factory
    return await make_charge(api_key)
