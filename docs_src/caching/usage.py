from lilya.apps import Lilya
from lilya.decorators import cache

app = Lilya()
file_cache = FileCache()


@app.get("/file-cache/{data}")
@cache(backend=file_cache, ttl=60)
async def file_cached_endpoint(data: str) -> dict:
    return {"data": data, "cached": True}
