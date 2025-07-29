from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.dependencies import Provide
from lilya.params import Header
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Dummy:
    def show(self):
        return "from-service"


class HeaderBasic(Controller):
    async def get(self, token: str = Header(value="X-API-TOKEN")):
        return {"token": token}


class HeaderRequired(Controller):
    async def get(self, token: str = Header(value="X-API-TOKEN", required=True)):
        return {"token": token}


class HeaderCasted(Controller):
    async def get(self, content_length: int = Header(value="Content-Length", cast=int)):
        return {"length": content_length}


class HeaderInvalidCast(Controller):
    async def get(self, content_length: int = Header(value="Content-Length", cast=int)):
        return {"length": content_length}


class HeaderMultiple(Controller):
    async def get(
        self,
        token: str = Header(value="X-TOKEN"),
        session: str = Header(value="X-SESSION"),
    ):
        return {"token": token, "session": session}


def test_header_basic(test_client_factory):
    with create_client(routes=[Path("/", HeaderBasic)], settings_module=EncoderSettings) as client:
        response = client.get("/", headers={"X-API-TOKEN": "secure123"})
        assert response.json() == {"token": "secure123"}


def test_header_required_missing(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderRequired)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


def test_header_casted(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderCasted)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"Content-Length": "123"})

        assert response.json() == {"length": 123}


def test_header_invalid_cast(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderInvalidCast)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"Content-Length": "abc"})

        assert response.status_code == 422


def test_header_multiple(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderMultiple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-TOKEN": "abc", "X-SESSION": "xyz"})

        assert response.json() == {"token": "abc", "session": "xyz"}


class HeaderWithPath(Controller):
    async def get(self, name: str, token: str = Header(value="X-TOKEN")):
        return {"name": name, "token": token}


def test_header_with_path(test_client_factory):
    with create_client(
        routes=[Path("/{name}", HeaderWithPath)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", headers={"X-TOKEN": "abc123"})
        assert response.json() == {"name": "lilya", "token": "abc123"}


class HeaderWithModel(Controller):
    async def get(self, user: User, token: str = Header(value="X-TOKEN")):
        return {"user": user.model_dump(), "token": token}


def test_header_with_model(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderWithModel)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", json={"name": "lilya", "age": 30}, headers={"X-TOKEN": "abc"})

        assert response.json() == {"user": {"name": "lilya", "age": 30}, "token": "abc"}


class HeaderWithModelAndDependency(Controller):
    async def get(self, user: User, service: Dummy, token: str = Header(value="X-TOKEN")):
        return {
            "user": user.model_dump(),
            "service": service.show(),
            "token": token,
        }


def test_header_with_model_and_dependency(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderWithModelAndDependency, dependencies={"service": Provide(Dummy)})],
        settings_module=EncoderSettings,
    ) as client:
        response = client.get(
            "/", json={"name": "tiago", "age": 35}, headers={"X-TOKEN": "secure"}
        )

        assert response.json() == {
            "user": {"name": "tiago", "age": 35},
            "service": "from-service",
            "token": "secure",
        }


class HeaderMissing(Controller):
    async def get(self, token: str = Header(value="X-REQUIRED", required=True)):
        return {"token": token}


def test_header_required_missing_case(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderMissing)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


class HeaderInvalid(Controller):
    async def get(self, token: int = Header(value="X-NUMERIC-TOKEN", cast=int)):
        return {"token": token}


def test_header_casted_invalid(test_client_factory):
    with create_client(
        routes=[Path("/", HeaderInvalid)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-NUMERIC-TOKEN": "abc"})

        assert response.status_code == 422
