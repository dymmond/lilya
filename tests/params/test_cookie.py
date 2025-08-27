from pydantic import BaseModel

from lilya.dependencies import Provide
from lilya.params import Cookie
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Dummy:
    def show(self):
        return "from-service"


async def cookie_basic(session: str = Cookie(value="csrftoken")):
    return {"session": session}


async def cookie_required(session: str = Cookie(value="csrftoken", required=True)):
    return {"session": session}


async def cookie_casted(visitor: int = Cookie(value="visit_count", cast=int)):
    return {"visitor": visitor}


async def cookie_invalid_cast(visitor: int = Cookie(value="visit_count", cast=int)):
    return {"visitor": visitor}


async def cookie_multiple(
    session: str = Cookie(value="csrftoken"),
    analytics: str = Cookie(value="ga_id"),
):
    return {"session": session, "analytics": analytics}


async def cookie_with_path(name: str, session: str = Cookie(value="csrftoken")):
    return {"name": name, "session": session}


async def cookie_with_model(user: User, session: str = Cookie(value="csrftoken")):
    return {"user": user.model_dump(), "session": session}


async def cookie_with_model_and_dependency(
    user: User, service: Dummy, session: str = Cookie(value="csrftoken")
):
    return {
        "user": user.model_dump(),
        "service": service.show(),
        "session": session,
    }


def test_cookie_basic(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_basic)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"csrftoken": "abc123"})
        assert response.json() == {"session": "abc123"}


def test_cookie_required_missing(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_required)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.status_code == 422


def test_cookie_casted(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_casted)], settings_module=EncoderSettings, debug=True
    ) as client:
        response = client.get("/", cookies={"visit_count": "5"})
        assert response.json() == {"visitor": 5}


def test_cookie_invalid_cast(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_invalid_cast)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"visit_count": "not-a-number"})
        assert response.status_code == 422


def test_cookie_multiple(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_multiple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"csrftoken": "abc", "ga_id": "xyz"})
        assert response.json() == {"session": "abc", "analytics": "xyz"}


def test_cookie_with_path(test_client_factory):
    with create_client(
        routes=[Path("/{name}", cookie_with_path)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", cookies={"csrftoken": "12345"})
        assert response.json() == {"name": "lilya", "session": "12345"}


def test_cookie_with_model(test_client_factory):
    with create_client(
        routes=[Path("/", cookie_with_model)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", json={"name": "lilya", "age": 2}, cookies={"csrftoken": "abc"})
        assert response.json() == {"user": {"name": "lilya", "age": 2}, "session": "abc"}


def test_cookie_with_model_and_dependency(test_client_factory):
    with create_client(
        routes=[
            Path("/", cookie_with_model_and_dependency, dependencies={"service": Provide(Dummy)})
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.get(
            "/", json={"name": "tiago", "age": 35}, cookies={"csrftoken": "secure"}
        )
        assert response.json() == {
            "user": {"name": "tiago", "age": 35},
            "service": "from-service",
            "session": "secure",
        }
