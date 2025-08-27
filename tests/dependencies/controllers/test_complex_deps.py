from dataclasses import dataclass

from pydantic import BaseModel

from lilya.controllers import Controller
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


class UserController(Controller):
    async def post(self, data: UserIn, service: UserDAO):
        return await service.create(**data.model_dump())


def test_service_with_pydantic():
    with create_client(
        routes=[
            Path(
                "/create",
                UserController,
                dependencies={
                    "service": Provide(UserDAO),
                },
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/create", json={"name": "lilya", "age": 18})
        assert response.status_code == 200, response.text
        assert response.json() == {"name": "lilya", "age": 18}


class UserControllerDep(Controller):
    dependencies = {
        "service": Provide(UserDAO),
    }

    async def post(self, data: UserIn, service: UserDAO):
        return await service.create(**data.model_dump())


def test_service_with_pydantic_controller_nested():
    with create_client(
        routes=[
            Path(
                "/create",
                UserControllerDep,
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/create", json={"name": "lilya", "age": 18})
        assert response.status_code == 200, response.text
        assert response.json() == {"name": "lilya", "age": 18}
