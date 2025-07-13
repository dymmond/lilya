from msgspec import Struct
from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


class TestBody(Controller):
    async def post(self, user: User):
        return user


class TestItem(Controller):
    async def post(self, item: Item):
        return item


def test_infer_body():
    data = {"name": "lilya", "age": 10}

    with create_client(
        routes=[Path("/infer", handler=TestBody, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10}


def test_infer_body_item():
    data = {"sku": "lilya"}

    with create_client(
        routes=[Path("/infer", handler=TestItem, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"sku": "lilya"}
