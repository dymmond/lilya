import pytest

from lilya.apps import Lilya
from lilya.dependencies import Provide, Resolve
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_sync_generator_dependency_injected_and_teardown():
    teardown = {"called": False}

    # a simple generator-based dependency
    def get_db():
        try:
            yield "MY_DB_CONN"
        finally:
            teardown["called"] = True

    # app with a route that uses Resolve(get_db)
    app = Lilya(
        dependencies={"db": Provide(get_db)},
        routes=[
            Path(
                "/check",
                handler=lambda db=Resolve(get_db): {"db_value": db},
            )
        ],
    )

    client = TestClient(app)

    # call the endpoint
    response = client.get("/check")
    assert response.status_code == 200
    assert response.json() == {"db_value": "MY_DB_CONN"}

    # after the request, our generator's finally block must have run
    assert teardown["called"] is True


async def test_async_generator_dependency_injected_and_teardown():
    teardown = {"called": False}

    # an async generator–based dependency
    async def get_async_db():
        try:
            yield "MY_ASYNC_DB"
        finally:
            teardown["called"] = True

    app = Lilya(
        dependencies={"db": Provide(get_async_db)},
        routes=[
            Path(
                "/async-check",
                handler=lambda db=Resolve(get_async_db): {"db_value": db},
            )
        ],
    )

    client = TestClient(app)

    response = client.get("/async-check")
    assert response.status_code == 200
    assert response.json() == {"db_value": "MY_ASYNC_DB"}

    # ensure cleanup ran
    assert teardown["called"] is True
