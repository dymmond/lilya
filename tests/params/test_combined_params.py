from pydantic import BaseModel

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


async def combined_basic(
    text: str = Query(alias="q"),
    token: str = Header(value="X-TOKEN"),
    session: str = Cookie(value="csrftoken"),
):
    return {"text": text, "token": token, "session": session}


async def combined_required(
    text: str = Query(alias="q", required=True),
    token: str = Header(value="X-TOKEN", required=True),
    session: str = Cookie(value="csrftoken", required=True),
):
    return {"text": text, "token": token, "session": session}


async def combined_cast(
    count: int = Query(alias="count", cast=int),
    num: int = Header(value="X-NUM", cast=int),
    visit: int = Cookie(value="visits", cast=int),
):
    return {"count": count, "num": num, "visit": visit}


async def combined_all_features(
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


def test_combined_basic(test_client_factory):
    with create_client(
        routes=[Path("/", combined_basic)], settings_module=EncoderSettings
    ) as client:
        resp = client.get(
            "/?q=hello", headers={"X-TOKEN": "tok123"}, cookies={"csrftoken": "sess456"}
        )
        assert resp.json() == {"text": "hello", "token": "tok123", "session": "sess456"}


def test_combined_required_missing_query(test_client_factory):
    with create_client(
        routes=[Path("/", combined_required)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/", headers={"X-TOKEN": "tok"}, cookies={"csrftoken": "sess"})
        assert resp.status_code == 422


def test_combined_required_missing_header(test_client_factory):
    with create_client(
        routes=[Path("/", combined_required)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?q=foo", cookies={"csrftoken": "sess"})
        assert resp.status_code == 422


def test_combined_required_missing_cookie(test_client_factory):
    with create_client(
        routes=[Path("/", combined_required)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?q=foo", headers={"X-TOKEN": "tok"})
        assert resp.status_code == 422


def test_combined_cast_valid(test_client_factory):
    with create_client(
        routes=[Path("/", combined_cast)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=5", headers={"X-NUM": "10"}, cookies={"visits": "3"})
        assert resp.json() == {"count": 5, "num": 10, "visit": 3}


def test_combined_cast_invalid_query(test_client_factory):
    with create_client(
        routes=[Path("/", combined_cast)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=bad", headers={"X-NUM": "10"}, cookies={"visits": "3"})
        assert resp.status_code == 422


def test_combined_cast_invalid_header(test_client_factory):
    with create_client(
        routes=[Path("/", combined_cast)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=1", headers={"X-NUM": "NaN"}, cookies={"visits": "3"})
        assert resp.status_code == 422


def test_combined_cast_invalid_cookie(test_client_factory):
    with create_client(
        routes=[Path("/", combined_cast)], settings_module=EncoderSettings
    ) as client:
        resp = client.get("/?count=1", headers={"X-NUM": "2"}, cookies={"visits": "oops"})
        assert resp.status_code == 422


def test_combined_with_model_and_dependency(test_client_factory):
    payload = {"name": "lilya", "age": 2}
    with create_client(
        routes=[Path("/", combined_all_features, dependencies={"service": Provide(Dummy)})],
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
