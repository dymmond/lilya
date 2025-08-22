from dataclasses import dataclass

from pydantic import BaseModel

from lilya.dependencies import Provide
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class DummyModel: ...


class UserIn(BaseModel):
    name: str
    age: int


@dataclass
class UserDAO:
    model: DummyModel = DummyModel()

    async def create(self, **data) -> DummyModel:
        return data


async def create_user(data: UserIn, service: UserDAO):
    return await service.create(**data.model_dump())


def test_service_with_pydantic():
    with create_client(
        routes=[
            Path(
                "/create",
                create_user,
                dependencies={
                    "service": Provide(UserDAO),
                },
                methods=["POST"],
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/create", json={"name": "lilya", "age": 18})
        assert response.status_code == 200, response.text
        assert response.json() == {"name": "lilya", "age": 18}
