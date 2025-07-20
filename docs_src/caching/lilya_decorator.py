from lilya.apps import Lilya
from lilya.caches.redis import RedisCache
from lilya.decorators import cache

app = Lilya()
redis_cache = RedisCache(redis_url="redis://localhost:6379")


@app.get("/data/{key}")
@cache(backend=redis_cache, ttl=30)
async def fetch_data(key: str) -> dict:
    return {"key": key, "value": key[::-1]}  # Simulating an expensive operation
