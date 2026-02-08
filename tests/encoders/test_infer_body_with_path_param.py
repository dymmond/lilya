from __future__ import annotations

from msgspec import Struct
from pydantic import BaseModel

from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


async def process_body(user: User, body_id: int):
    return {"body_id": body_id, "name": user.name, "age": user.age}


async def process_item(item_id: int, item: Item):
    return {"id": int(item_id), "sku": item.sku}


def test_infer_body(test_client_factory):
    data = {"name": "lilya", "age": 10}

    with create_client(
        routes=[Path("/infer/{body_id}", handler=process_body, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/infer/2", json=data)

        assert response.status_code == 200
        assert response.json() == {"body_id": "2", "name": "lilya", "age": 10}


def test_infer_body_item(test_client_factory):
    data = {"sku": "lilya"}

    with create_client(
        routes=[Path("/infer/{item_id}", handler=process_item, methods=["PATCH"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.patch("/infer/1", json=data)

        assert response.status_code == 200
        assert response.json() == {"id": 1, "sku": "lilya"}
