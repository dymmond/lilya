import pytest

from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.dependencies import Provide, Resolve
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_sync_generator_dependency_injected_and_teardown():
    def get_db():
        try:
            yield "MY_DB_CONN"
        finally:
            ...

    class Test(Controller):
        async def get(self, db=Resolve(get_db)):
            return {"db_value": db}

    # app with a route that uses Resolve(get_db)
    app = Lilya(
        dependencies={"db": Provide(get_db)},
        routes=[
            Path(
                "/check",
                handler=Test,
            )
        ],
    )

    client = TestClient(app)

    # call the endpoint
    response = client.get("/check")
    assert response.status_code == 200
    assert response.json() == {"db_value": "MY_DB_CONN"}


async def test_async_generator_dependency_injected_and_teardown():
    # an async generator–based dependency
    async def get_async_db():
        try:
            yield "MY_ASYNC_DB"
        finally:
            ...

    class Test(Controller):
        async def get(self, db=Resolve(get_async_db)):
            return {"db_value": db}

    app = Lilya(
        dependencies={"db": Provide(get_async_db)},
        routes=[
            Path(
                "/async-check",
                handler=Test,
            )
        ],
    )

    client = TestClient(app)

    response = client.get("/async-check")
    assert response.status_code == 200
    assert response.json() == {"db_value": "MY_ASYNC_DB"}
