from typing import Any

from pydantic import BaseModel

from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class DummyService:
    def show(self):
        return "works"


def base_model(user: User, service=Provides()) -> dict[str, Any]:
    return {**user.model_dump(), "show": service.show()}


def test_pydantic_custom_response(test_client_factory):
    data = {"name": "Lilya", "age": 3}
    with create_client(
        settings_module=EncoderSettings,
        routes=[Path("/", base_model, dependencies={"service": Provide(DummyService)})],
    ) as client:
        response = client.get("/", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "Lilya", "age": 3, "show": "works"}


class Item(BaseModel):
    name: str


def multiple(user: User, item: Item, service=Provides()) -> dict[str, Any]:
    return {"user": user.model_dump(), "item": item.model_dump(), "show": service.show()}


def test_multiple(test_client_factory):
    data = {"user": {"name": "Lilya", "age": 3}, "item": {"name": "test"}}

    with create_client(
        settings_module=EncoderSettings,
        routes=[Path("/", multiple, dependencies={"service": Provide(DummyService)})],
    ) as client:
        response = client.get("/", json=data)

        assert response.status_code == 200
        assert response.json() == {
            "user": {"name": "Lilya", "age": 3},
            "item": {"name": "test"},
            "show": "works",
        }
