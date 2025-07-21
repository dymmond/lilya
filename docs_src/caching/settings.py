from lilya.conf.global_settings import Settings
from lilya.caches.redis import RedisCache
from lilya.protocols.cache import CacheBackend


class CustomSettings(Settings):
    cache_backend: CacheBackend = RedisCache(redis_url="redis://localhost:6379")
