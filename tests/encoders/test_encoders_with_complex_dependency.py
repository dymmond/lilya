from typing import Any

from msgspec import Struct
from pydantic import BaseModel

from lilya.dependencies import Provide
from lilya.encoders import Encoder, register_encoder
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


def get_db():
    return "db_session"


class ATestService:
    def test(self):
        return "test_service"


class PydanticEncoder(Encoder):
    __type__ = BaseModel
    name = "ModelDumpEncoder"

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        return obj.model_dump()

    def encode(self, structure: type[BaseModel], value: Any) -> Any:
        return structure(**value)


class NewSettings(EncoderSettings):
    def __post_init__(self) -> None:
        register_encoder(PydanticEncoder())

    @property
    def dependencies(self) -> dict:
        """
        Returns the default dependencies for the application.
        """

        return {
            "session": Provide(get_db),
        }


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


async def process_body(user: User, body_id: int, service: ATestService, session: Any):
    return {"body_id": body_id, "name": user.name, "age": user.age}


def test_infer_body(test_client_factory):
    data = {"name": "lilya", "age": 10}

    with create_client(
        routes=[
            Path(
                "/infer/{body_id}",
                handler=process_body,
                methods=["POST"],
                dependencies={
                    "service": Provide(ATestService),
                },
            )
        ],
        settings_module=NewSettings,
    ) as client:
        response = client.post("/infer/2", json=data)

        assert response.status_code == 200
        assert response.json() == {"body_id": "2", "name": "lilya", "age": 10}


async def process_body_with_dependency_multiple(
    item_id: int, user: User, item: Item, service: ATestService, session: Any
):
    return {
        "id": item_id,
        **user.model_dump(),
        "sku": item.sku,
        "service": service.test(),
        "session": session,
    }


def test_infer_body_with_dependency_multiple(test_client_factory):
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": "test"}}

    with create_client(
        routes=[
            Path(
                "/infer/{item_id}",
                handler=process_body_with_dependency_multiple,
                methods=["POST"],
                dependencies={
                    "service": Provide(ATestService),
                },
            ),
        ],
        settings_module=NewSettings,
    ) as client:
        response = client.post("/infer/1", json=data)

        assert response.status_code == 200
        assert response.json() == {
            "id": "1",
            "name": "lilya",
            "age": 10,
            "sku": "test",
            "service": "test_service",
            "session": "db_session",
        }


async def process_body_simple(user: User, service: ATestService, session: Any):
    return {"name": user.name, "age": user.age}


def test_process_body_simple(test_client_factory):
    data = {"name": "lilya", "age": 10}

    with create_client(
        routes=[
            Path(
                "/infer",
                handler=process_body_simple,
                methods=["POST"],
                dependencies={
                    "service": Provide(ATestService),
                },
            )
        ],
        settings_module=NewSettings,
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 10}
