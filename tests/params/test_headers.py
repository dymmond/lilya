from pydantic import BaseModel

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


async def header_basic(token: str = Header(value="X-API-TOKEN")):
    return {"token": token}


async def header_required(token: str = Header(value="X-API-TOKEN", required=True)):
    return {"token": token}


async def header_casted(content_length: int = Header(value="Content-Length", cast=int)):
    return {"length": content_length}


async def header_typed_list(role: list[str] = Header(value="X-ROLE", cast=list[str])):
    return {"role": role}


async def header_typed_dict(meta: dict[str, int] = Header(value="X-META", cast=dict[str, int])):
    return {"meta": meta}


async def header_invalid_cast(content_length: int = Header(value="Content-Length", cast=int)):
    return {"length": content_length}


async def header_multiple(
    token: str = Header(value="X-TOKEN"),
    session: str = Header(value="X-SESSION"),
):
    return {"token": token, "session": session}


def test_header_basic(test_client_factory):
    with create_client(
        routes=[Path("/", header_basic)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-API-TOKEN": "secure123"})
        assert response.json() == {"token": "secure123"}


def test_header_required_missing(test_client_factory):
    with create_client(
        routes=[Path("/", header_required)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


def test_header_casted():
    with create_client(
        routes=[Path("/", header_casted)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"Content-Length": "123"})

        assert response.json() == {"length": 123}


def test_header_typed_list_single(test_client_factory):
    with create_client(
        routes=[Path("/", header_typed_list)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-ROLE": "admin"})

        assert response.json() == {"role": ["admin"]}


def test_header_typed_list_multiple(test_client_factory):
    with create_client(
        routes=[Path("/", header_typed_list)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers=[("X-ROLE", "admin"), ("X-ROLE", "staff")])

        assert response.json() == {"role": ["admin", "staff"]}


def test_header_typed_dict(test_client_factory):
    with create_client(
        routes=[Path("/", header_typed_dict)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-META": '{"page":"2","limit":10}'})

        assert response.json() == {"meta": {"page": 2, "limit": 10}}


def test_header_invalid_cast(test_client_factory):
    with create_client(
        routes=[Path("/", header_invalid_cast)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"Content-Length": "abc"})

        assert response.status_code == 422


def test_header_multiple(test_client_factory):
    with create_client(
        routes=[Path("/", header_multiple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-TOKEN": "abc", "X-SESSION": "xyz"})

        assert response.json() == {"token": "abc", "session": "xyz"}


async def header_with_path(name: str, token: str = Header(value="X-TOKEN")):
    return {"name": name, "token": token}


def test_header_with_path(test_client_factory):
    with create_client(
        routes=[Path("/{name}", header_with_path)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", headers={"X-TOKEN": "abc123"})
        assert response.json() == {"name": "lilya", "token": "abc123"}


async def header_with_model(user: User, token: str = Header(value="X-TOKEN")):
    return {"user": user.model_dump(), "token": token}


def test_header_with_model(test_client_factory):
    with create_client(
        routes=[Path("/", header_with_model)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", json={"name": "lilya", "age": 30}, headers={"X-TOKEN": "abc"})

        assert response.json() == {"user": {"name": "lilya", "age": 30}, "token": "abc"}


async def header_with_model_and_dependency(
    user: User, service: Dummy, token: str = Header(value="X-TOKEN")
):
    return {
        "user": user.model_dump(),
        "service": service.show(),
        "token": token,
    }


def test_header_with_model_and_dependency(test_client_factory):
    with create_client(
        routes=[
            Path("/", header_with_model_and_dependency, dependencies={"service": Provide(Dummy)})
        ],
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


async def header_required_missing(token: str = Header(value="X-REQUIRED", required=True)):
    return {"token": token}


def test_header_required_missing_case(test_client_factory):
    with create_client(
        routes=[Path("/", header_required_missing)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


async def header_casted_invalid(token: int = Header(value="X-NUMERIC-TOKEN", cast=int)):
    return {"token": token}


def test_header_casted_invalid(test_client_factory):
    with create_client(
        routes=[Path("/", header_casted_invalid)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", headers={"X-NUMERIC-TOKEN": "abc"})

        assert response.status_code == 422
