from uuid import UUID, uuid4

from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.controllers import Controller
from lilya.decorators import cache
from lilya.routing import Path
from lilya.testclient import TestClient, create_client
from tests.encoders.settings import EncoderSettings


class Item(BaseModel):
    id: int
    name: str


def test_basic_caching_memory(memory_cache, test_client_factory) -> None:
    @cache(backend=memory_cache)
    async def items_view(data: Item) -> Item:
        return data

    with create_client(
        routes=[Path("/items", handler=items_view, methods=["POST"])],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/items", json={"id": 1, "name": "Test Item"})
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Test Item"}


def test_controller_caching(memory_cache, test_client_factory) -> None:
    class ItemsController(Controller):
        @cache(backend=memory_cache)
        async def post(self, data: Item) -> Item:
            return data

    with create_client(
        routes=[Path("/items", handler=ItemsController)], settings_module=EncoderSettings
    ) as client:
        response = client.post("/items", json={"id": 1, "name": "Test Item"})
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Test Item"}


class ItemWithUUID(BaseModel):
    id: UUID
    name: str


def test_controller_caching_with_uuid(memory_cache, test_client_factory) -> None:
    app = Lilya(settings_module=EncoderSettings, debug=True)

    @app.get("/items/{item_id}")
    @cache(backend=memory_cache)
    async def get_item(item_id: UUID) -> ItemWithUUID:
        return {"id": item_id, "name": "Test Item"}

    @app.put("/items/{item_id}")
    @cache(backend=memory_cache)
    async def update_item(item_id: UUID, data: ItemWithUUID) -> ItemWithUUID:
        return {"id": item_id, "name": data.name}

    @app.patch("/items/{item_id}")
    @cache(backend=memory_cache)
    async def patch_item(item_id: UUID, data: ItemWithUUID) -> ItemWithUUID:
        return {"id": item_id, "name": data.name}

    @app.delete("/items/{item_id}")
    @cache(backend=memory_cache)
    async def delete_item(item_id: UUID) -> None:
        return None

    @app.post("/items")
    @cache(backend=memory_cache)
    async def create_item(data: ItemWithUUID) -> ItemWithUUID:
        return data

    headers = {"Content-Type": "application/json"}
    payload = {"id": uuid4().hex, "name": "Test Item"}

    client = TestClient(app)

    response = client.get(f"/items/{payload['id']}", json=payload, headers=headers)
    assert response.status_code == 200
    assert UUID(response.json()["id"]).hex == payload["id"]
    assert response.json()["name"] == payload["name"]

    response = client.post("/items", json=payload, headers=headers)
    assert response.status_code == 200
    assert UUID(response.json()["id"]).hex == payload["id"]
    assert response.json()["name"] == payload["name"]

    response = client.put(f"/items/{payload['id']}", json=payload, headers=headers)
    assert response.status_code == 200
    assert UUID(response.json()["id"]).hex == payload["id"]
    assert response.json()["name"] == payload["name"]

    response = client.patch(f"/items/{payload['id']}", json=payload, headers=headers)
    assert response.status_code == 200
    assert UUID(response.json()["id"]).hex == payload["id"]
    assert response.json()["name"] == payload["name"]

    response = client.delete(f"/items/{payload['id']}", headers=headers)
    assert response.status_code == 200

    item_id = payload["id"]
    response = client.get(f"/items/{item_id}", headers=headers)
    assert response.status_code == 200
    assert UUID(response.json()["id"]).hex == item_id
