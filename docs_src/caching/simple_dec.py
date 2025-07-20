from lilya.apps import Lilya
from lilya.decorators import cache


app = Lilya()

@app.get("/expensive/{value}")
@cache(ttl=10)  # Cache for 10 seconds
async def expensive_operation(value: int) -> dict:
    return {"result": value * 2}
