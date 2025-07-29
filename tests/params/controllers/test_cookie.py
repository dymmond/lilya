from pydantic import BaseModel

from lilya.controllers import Controller
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


class CookieBasic(Controller):
    async def get(self, session: str = Cookie(value="csrftoken")):
        return {"session": session}


class CookieRequired(Controller):
    async def get(self, session: str = Cookie(value="csrftoken", required=True)):
        return {"session": session}


class CookieCasted(Controller):
    async def get(self, visit_count: int = Cookie(value="visit_count", cast=int)):
        return {"visit_count": visit_count}


class CookieInvalidCast(Controller):
    async def get(self, visit_count: int = Cookie(value="visit_count", cast=int)):
        return {"visit_count": visit_count}


class CookieMultiple(Controller):
    async def get(
        self,
        session: str = Cookie(value="csrftoken"),
        analytics: str = Cookie(value="ga_id"),
    ):
        return {"session": session, "analytics": analytics}


class CookieWithPath(Controller):
    async def get(self, name: str, session: str = Cookie(value="csrftoken")):
        return {"name": name, "session": session}


class CookieWithModel(Controller):
    async def get(self, user: User, session: str = Cookie(value="csrftoken")):
        return {"user": user.model_dump(), "session": session}


class CookieWithModelAndDependency(Controller):
    async def get(self, user: User, service: Dummy, session: str = Cookie(value="csrftoken")):
        return {
            "user": user.model_dump(),
            "service": service.show(),
            "session": session,
        }


class CookieMissing(Controller):
    async def get(self, session: str = Cookie(value="csrftoken", required=True)):
        return {"session": session}


class CookieInvalid(Controller):
    async def get(self, session: int = Cookie(value="visit_count", cast=int)):
        return {"session": session}


def test_cookie_basic(test_client_factory):
    with create_client(routes=[Path("/", CookieBasic)], settings_module=EncoderSettings) as client:
        response = client.get("/", cookies={"csrftoken": "abc123"})
        assert response.json() == {"session": "abc123"}


def test_cookie_required_missing(test_client_factory):
    with create_client(
        routes=[Path("/", CookieRequired)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.status_code == 422


def test_cookie_casted(test_client_factory):
    with create_client(
        routes=[Path("/", CookieCasted)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"visit_count": "5"})
        assert response.json() == {"visit_count": 5}


def test_cookie_invalid_cast(test_client_factory):
    with create_client(
        routes=[Path("/", CookieInvalidCast)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"visit_count": "not-number"})
        assert response.status_code == 422


def test_cookie_multiple(test_client_factory):
    with create_client(
        routes=[Path("/", CookieMultiple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"csrftoken": "s1", "ga_id": "g1"})
        assert response.json() == {"session": "s1", "analytics": "g1"}


def test_cookie_with_path(test_client_factory):
    with create_client(
        routes=[Path("/{name}", CookieWithPath)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", cookies={"csrftoken": "xyz"})
        assert response.json() == {"name": "lilya", "session": "xyz"}


def test_cookie_with_model(test_client_factory):
    payload = {"name": "lilya", "age": 2}
    with create_client(
        routes=[Path("/", CookieWithModel)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", json=payload, cookies={"csrftoken": "abc"})
        assert response.json() == {"user": payload, "session": "abc"}


def test_cookie_with_model_and_dependency(test_client_factory):
    payload = {"name": "tiago", "age": 35}
    with create_client(
        routes=[Path("/", CookieWithModelAndDependency, dependencies={"service": Provide(Dummy)})],
        settings_module=EncoderSettings,
    ) as client:
        response = client.get("/", json=payload, cookies={"csrftoken": "secure"})
        assert response.json() == {
            "user": payload,
            "service": "from-service",
            "session": "secure",
        }


def test_cookie_missing_case(test_client_factory):
    with create_client(
        routes=[Path("/", CookieMissing)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.status_code == 422


def test_cookie_invalid_case(test_client_factory):
    with create_client(
        routes=[Path("/", CookieInvalid)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/", cookies={"visit_count": "oops"})
        assert response.status_code == 422
