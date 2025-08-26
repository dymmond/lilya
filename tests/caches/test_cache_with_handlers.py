from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.decorators import cache
from lilya.routing import Path
from lilya.testclient import create_client
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
