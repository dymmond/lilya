import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import lilya
from lilya.apps import Lilya
from lilya.dependencies import Depends, Provide, inject
from lilya.requests import Request
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


class RedisClient:
    def __init__(self, dsn="local"):
        self.dsn = dsn


def redis_client() -> RedisClient:
    return RedisClient(dsn="injected_dsn")


@inject
def depends_on_redis(
    client=Depends(redis_client),
) -> str:
    return client


@pytest_asyncio.fixture()
async def async_client():
    app = Lilya(dependencies={"redis": Provide(depends_on_redis)})

    @app.get("/inject")
    async def data_endpoint(
        redis: RedisClient,
    ) -> str:
        return redis.dsn

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def test_dependency_precedence():
    app = Lilya()

    @app.get("/", dependencies={"client": Provide(RedisClient, dsn="default_dsn")})
    async def data_endpoint(
        client: RedisClient,
    ) -> str:
        return client.dsn

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == "default_dsn"


async def test_dependency_injection_precedence(async_client):
    response = await async_client.get("/inject")

    assert response.status_code == 200
    assert response.json() == "injected_dsn"


async def test_nested_depends_resolution():
    """
    Nested Depends() should resolve inner dependency correctly.
    """

    def inner():
        return "inner"

    def outer(value=Depends(inner)):
        return f"outer:{value}"

    @inject
    async def service(dep=Depends(outer)):
        return dep

    result = await service()
    assert result == "outer:inner"


async def test_callable_value_injection(test_client_factory):
    """
    Provide should accept a callable and resolve correctly.
    """

    def make_value():
        return "called"

    app = Lilya(dependencies={"x": Provide(make_value)})

    @app.get("/value")
    async def route(x: str):
        return x

    client = TestClient(app)
    response = client.get("/value")

    assert response.status_code == 200
    assert response.json() == "called"


async def test_literal_value_injection(test_client_factory):
    """
    Provide should inject a literal pre-created value.
    """
    instance = RedisClient(dsn="literal")

    app = Lilya(dependencies={"redis": Provide(lambda: instance)})

    @app.get("/literal")
    async def route(redis: RedisClient):
        return redis.dsn

    client = TestClient(app)
    response = client.get("/literal")

    assert response.status_code == 200
    assert response.json() == "literal"


async def test_caching_behavior(test_client_factory):
    """
    Provide(use_cache=True) should reuse the same instance.
    """
    counter = {"calls": 0}

    def factory():
        counter["calls"] += 1
        return RedisClient(dsn=f"dsn-{counter['calls']}")

    app = Lilya(dependencies={"redis": Provide(factory, use_cache=True)})

    @app.get("/cache")
    async def route(redis: RedisClient):
        return redis.dsn

    client = TestClient(app)

    first = client.get("/cache")
    second = client.get("/cache")

    assert first.json() == second.json() == "dsn-1"
    assert counter["calls"] == 1


async def test_request_injection_with_custom_name(test_client_factory):
    """
    Ensure that dependencies receive the request object even if the parameter name is not 'request'.
    """

    async def get_app_version(conn: Request):
        # Should access the app via conn and return version from settings
        return getattr(conn.app, "version", "unknown")

    app = Lilya(dependencies={"version_info": Provide(get_app_version)})

    # Add version attribute to simulate app.settings.version

    @app.get("/version")
    async def route(version_info: str):
        return version_info

    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == lilya.__version__
