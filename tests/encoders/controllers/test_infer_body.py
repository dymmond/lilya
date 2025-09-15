from typing import Any

from msgspec import Struct
from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


class Test(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=Test, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


class TestWithDep(Controller):
    async def post(self, user: User, item: Item, x=Provides()):
        return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestWithDep, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


class TestOptDep(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body_with_dependency_not_passed(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestOptDep, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}


class TestOptDepNP(Controller):
    async def post(self, user: User, item: Item, x: Any):
        return {**user.model_dump(), "sku": item.sku, "x": x}


def test_infer_body_with_dependency_without_provides(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=TestOptDepNP, methods=["POST"])],
        dependencies={"x": Provide(lambda: "app_value")},
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test", "x": "app_value"}


class FormController(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body_from_form(test_client_factory):
    data = {"user": '{"name": "lilya", "age": 10}', "item": '{"sku": "test"}'}

    with create_client(
        routes=[Path("/infer-form", handler=FormController)],
        settings_module=EncoderSettings,
    ) as client:
        # send as form
        response = client.post("/infer-form", data=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10, "sku": "test"}
