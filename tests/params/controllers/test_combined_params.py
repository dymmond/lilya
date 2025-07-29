from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.dependencies import Provide
from lilya.params import Cookie, Header, Query
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Dummy:
    def show(self):
        return "service-result"


class CombinedBasicController(Controller):
    async def get(
        self,
        text: str = Query(alias="q"),
        token: str = Header(value="X-TOKEN"),
        session: str = Cookie(value="csrftoken"),
    ):
        return {"text": text, "token": token, "session": session}


class CombinedRequiredController(Controller):
    async def get(
        self,
        text: str = Query(alias="q", required=True),
        token: str = Header(value="X-TOKEN", required=True),
        session: str = Cookie(value="csrftoken", required=True),
    ):
        return {"text": text, "token": token, "session": session}


class CombinedCastController(Controller):
    async def get(
        self,
        count: int = Query(alias="count", cast=int),
        num: int = Header(value="X-NUM", cast=int),
        visit: int = Cookie(value="visits", cast=int),
    ):
        return {"count": count, "num": num, "visit": visit}


class CombinedAllFeaturesController(Controller):
    async def get(
        self,
        user: User,
        service: Dummy,
        q: str = Query(default="none"),
        token: str = Header(value="X-TOKEN"),
        session: str = Cookie(value="csrftoken"),
    ):
        return {
            "user": user.model_dump(),
            "q": q,
            "token": token,
            "session": session,
            "service": service.show(),
        }


def test_combined_basic_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedBasicController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get(
            "/?q=hello", headers={"X-TOKEN": "tok123"}, cookies={"csrftoken": "sess456"}
        )
        assert resp.json() == {"text": "hello", "token": "tok123", "session": "sess456"}


def test_combined_required_missing_query_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedRequiredController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/", headers={"X-TOKEN": "tok"}, cookies={"csrftoken": "sess"})
        assert resp.status_code == 422


def test_combined_required_missing_header_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedRequiredController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?q=foo", cookies={"csrftoken": "sess"})
        assert resp.status_code == 422


def test_combined_required_missing_cookie_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedRequiredController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?q=foo", headers={"X-TOKEN": "tok"})
        assert resp.status_code == 422


def test_combined_cast_valid_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedCastController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=5", headers={"X-NUM": "10"}, cookies={"visits": "3"})
        assert resp.json() == {"count": 5, "num": 10, "visit": 3}


def test_combined_cast_invalid_query_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedCastController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=bad", headers={"X-NUM": "10"}, cookies={"visits": "3"})
        assert resp.status_code == 422


def test_combined_cast_invalid_header_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedCastController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=1", headers={"X-NUM": "NaN"}, cookies={"visits": "3"})
        assert resp.status_code == 422


def test_combined_cast_invalid_cookie_controller(test_client_factory):
    with create_client(
        routes=[Path("/", CombinedCastController)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=1", headers={"X-NUM": "2"}, cookies={"visits": "oops"})
        assert resp.status_code == 422


def test_combined_with_model_and_dependency_controller(test_client_factory):
    payload = {"name": "lilya", "age": 2}
    with create_client(
        routes=[
            Path("/", CombinedAllFeaturesController, dependencies={"service": Provide(Dummy)})
        ],
        settings_module=EncoderSettings,
    ) as client:
        resp = client.get(
            "/?q=test", headers={"X-TOKEN": "tok"}, cookies={"csrftoken": "sess"}, json=payload
        )
        assert resp.json() == {
            "user": payload,
            "q": "test",
            "token": "tok",
            "session": "sess",
            "service": "service-result",
        }
