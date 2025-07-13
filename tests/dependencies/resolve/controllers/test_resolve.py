from typing import Any

import pytest

from lilya.controllers import Controller
from lilya.dependencies import Provide, Provides, Resolve
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.testclient import create_client

pytestmark = pytest.mark.anyio


def get_user():
    return {"id": 1, "name": "John Doe"}


def get_current_user(user: dict[str, Any] = Resolve(get_user)) -> dict[str, Any]:
    return user


async def get_async_user():
    return {"id": 2, "name": "Jane Doe"}


async def async_endpoint(current_user: Any = Resolve(get_async_user)):
    return {"message": "Hello", "user": current_user}


def endpoint(current_user: Any = Resolve(get_current_user)):
    return {"message": "Hello", "user": current_user}


class Test(Controller):
    async def get(self, current_user: Any = Provides()) -> JSONResponse:
        return JSONResponse({"message": "Hello", "user": current_user})


def test_use_requires_in_function_dependencies_using_provide(test_client_factory):
    with create_client(
        routes=[
            Path(
                "/requires",
                handler=Test,
                dependencies={
                    "current_user": Provide(get_current_user),
                },
            ),
        ]
    ) as client:
        response = client.get("/requires")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello", "user": {"id": 1, "name": "John Doe"}}


class TestRequires(Controller):
    async def get(
        self,
        current_user: dict[str, Any] | None = Resolve(endpoint),
    ) -> JSONResponse:
        return JSONResponse(current_user)


def test_use_resolve_as_a_non_dependency_union(test_client_factory):
    with create_client(
        routes=[
            Path("/resolve-simple-union", handler=TestRequires),
        ]
    ) as client:
        response = client.get("/resolve-simple-union")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello", "user": {"id": 1, "name": "John Doe"}}
