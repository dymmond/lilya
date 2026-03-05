from __future__ import annotations

import re
import uuid
from typing import Any

import pytest
import pytest_asyncio

from lilya.apps import Lilya
from lilya.caches.memory import InMemoryCache
from lilya.caches.redis import RedisCache
from lilya.conf import settings
from lilya.testclient import TestClient
from tests.settings import AppTestSettings

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

CACHE_TTL = 10  # 10 seconds for quick TTL tests


def pytest_configure(config):
    config.option.asyncio_mode = "auto"


class NamespacedRedisCache(RedisCache):
    """Redis cache wrapper that prefixes keys to isolate tests in parallel workers."""

    def __init__(self, redis_url: str, namespace: str) -> None:
        super().__init__(redis_url)
        self.namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Any | None:
        return await super().get(self._key(key))

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await super().set(self._key(key), value, ttl)

    async def delete(self, key: str) -> None:
        await super().delete(self._key(key))

    def sync_get(self, key: str) -> Any | None:
        return super().sync_get(self._key(key))

    def sync_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        super().sync_set(self._key(key), value, ttl)

    def sync_delete(self, key: str) -> None:
        super().sync_delete(self._key(key))


def _safe_node_id(node_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", node_id)


async def _delete_namespace(client: Any, namespace: str) -> None:
    pattern = f"{namespace}:*"
    cursor: int | str = 0
    while True:
        cursor, keys = await client.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            await client.delete(*keys)
        if str(cursor) == "0":
            break


@pytest.fixture(scope="function")
def memory_cache() -> InMemoryCache:
    """Fixture providing a fresh InMemoryCache instance."""
    return InMemoryCache()


@pytest_asyncio.fixture(scope="function")
async def redis_cache(request: pytest.FixtureRequest) -> RedisCache:
    """Fixture providing a fresh RedisCache instance with proper setup and cleanup."""
    if redis is None:
        pytest.skip("redis is not installed")

    worker_input = getattr(request.config, "workerinput", {})
    worker_id = worker_input.get("workerid", "master")
    namespace = f"pytest:{worker_id}:{_safe_node_id(request.node.nodeid)}:{uuid.uuid4().hex}"

    cache = NamespacedRedisCache("redis://localhost", namespace)

    # Ensure async_client is set before tests
    cache.async_client = redis.Redis.from_url("redis://localhost", decode_responses=False)

    yield cache

    await _delete_namespace(cache.async_client, namespace)

    # Ensure Redis connection is properly closed before loop ends
    try:
        await cache.close()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@pytest.fixture(scope="function")
async def redis_settings(redis_cache) -> AppTestSettings:
    """Fixture providing Redis settings for testing."""

    class RedisSettings(AppTestSettings):
        cache_backend: RedisCache = redis_cache

    setts = RedisSettings()
    return setts


@pytest.fixture(scope="function")
def lilya_app(redis_cache) -> Lilya:
    """Fixture for an Lilya app with caching."""
    app = Lilya()

    @app.get("/cache/{key}")
    async def get_cache_value(key: str) -> Any:
        return await settings.cache_backend.get(key)

    @app.get("/set-cache/{key}/{value}")
    async def set_cache_value(key: str, value: str) -> str:
        await settings.cache_backend.set(key, value, CACHE_TTL)
        return "Cached"

    @app.get("/delete-cache/{key}")
    async def delete_cache_value(key: str) -> str:
        await settings.cache_backend.delete(key)
        return "Deleted"

    return app


@pytest.fixture(scope="function")
def client(lilya_app: Lilya) -> TestClient:
    """Fixture for an Lilya test client."""
    return TestClient(lilya_app)
