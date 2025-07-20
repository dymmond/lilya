from dataclasses import dataclass, field
from lilya.conf.global_settings import Settings
from lilya.caches.redis import RedisCache
from lilya.protocols.cache import CacheBackend


@dataclass
class CustomSettings(Settings):
    cache_backend: CacheBackend = field(default=RedisCache(redis_url="redis://localhost:6379"))
