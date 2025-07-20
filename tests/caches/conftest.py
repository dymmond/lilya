from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio

from lilya.apps import Lilya
from lilya.caches.memory import InMemoryCache
from lilya.caches.redis import RedisCache
from lilya.conf import settings
from lilya.testclient import TestClient
from tests.settings import TestSettings

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

CACHE_TTL = 10  # 10 seconds for quick TTL tests


def pytest_configure(config):
    config.option.asyncio_mode = "auto"


@pytest.fixture(scope="function")
def memory_cache() -> InMemoryCache:
    """Fixture providing a fresh InMemoryCache instance."""
    return InMemoryCache()


@pytest_asyncio.fixture(scope="function")
async def redis_cache() -> RedisCache:
    """Fixture providing a fresh RedisCache instance with proper setup and cleanup."""
    cache = RedisCache("redis://localhost")

    # Ensure async_client is set before tests
    cache.async_client = redis.Redis.from_url("redis://localhost", decode_responses=False)

    await cache.async_client.flushdb()  # Ensure a clean test environment

    yield cache

    # Ensure Redis connection is properly closed before loop ends
    try:
        await cache.close()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@pytest.fixture(scope="function")
async def redis_settings(redis_cache) -> TestSettings:
    """Fixture providing Redis settings for testing."""

    class RedisSettings(TestSettings):
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
