import pytest
from pydantic import BaseModel

from lilya.dependencies import Provide
from lilya.params import Query
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


class User(BaseModel):
    name: str
    age: int


class Dummy:
    def show(self):
        return "test"


def test_query_for_boolean(test_client_factory):
    query = Query(default="false")
    query.resolve(query.default, bool)

    assert query.default is False

    query = Query(default="true", cast=bool)
    query.resolve(query.default, bool)

    assert query.default is True


async def inject_query_param_bool(name: str, by_me: int = Query(cast=bool)):
    return {"name": name, "search": by_me}


@pytest.mark.parametrize(
    "value, expected",
    [
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        (1, True),
        (0, False),
        (True, True),
        (False, False),
    ],
)
def test_inject_query_param_bool(test_client_factory, value, expected):
    with create_client(
        routes=[Path("/{name}", inject_query_param_bool)], settings_module=EncoderSettings
    ) as client:
        response = client.get(f"/lilya?by_me={value}")

        assert response.json() == {"name": "lilya", "search": expected}


async def inject_query_params(name: str, q: str = Query()):
    return {"name": name, "search": q}


def test_inject_query_params(test_client_factory):
    with create_client(
        routes=[Path("/{name}", inject_query_params)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya?q=result")

        assert response.json() == {"name": "lilya", "search": "result"}


async def inject_query_params_model(user: User, name: str, q=Query()):
    return {"user": user.model_dump(), "name": name, "search": q}


def test_with_models(test_client_factory):
    data = {"name": "lilya", "age": 2}

    with create_client(
        routes=[Path("/{name}", inject_query_params_model)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", json=data)
        assert response.json() == {
            "user": {"name": "lilya", "age": 2},
            "name": "lilya",
            "search": None,
        }


async def inject_query_params_simple(name: str = Query(), q: str = Query()):
    return {"name": name, "search": q}


def test_inject_query_params_simple(test_client_factory):
    with create_client(
        routes=[Path("/", inject_query_params_simple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/?name=lilya&q=result")

        assert response.json() == {"name": "lilya", "search": "result"}


async def inject_query_params_simpler(name: str = Query(), q: str = Query()):
    return {"name": name, "search": q}


def test_inject_query_params_simpler(test_client_factory):
    with create_client(
        routes=[Path("/", inject_query_params_simpler)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/?q=result")

        assert response.json() == {"name": None, "search": "result"}


async def inject_query_params_model_with_inject(user: User, name: str, service: Dummy, q=Query()):
    return {"user": user.model_dump(), "service": service.show(), "name": name, "search": q}


def test_with_models_with_inject(test_client_factory):
    data = {"name": "lilya", "age": 2}

    with create_client(
        routes=[
            Path(
                "/{name}",
                inject_query_params_model_with_inject,
                dependencies={"service": Provide(Dummy)},
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.get("/lilya", json=data)
        assert response.json() == {
            "user": {"name": "lilya", "age": 2},
            "service": "test",
            "name": "lilya",
            "search": None,
        }


async def required_param(q: str = Query(required=True)):
    return {"q": q}


def test_required_query_param_missing(test_client_factory):
    with create_client(
        routes=[Path("/", required_param)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


async def query_with_defaults(page: int = Query(default=1), limit: int = Query(default=10)):
    return {"page": page, "limit": limit}


def test_query_defaults(test_client_factory):
    with create_client(
        routes=[Path("/", query_with_defaults)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.json() == {"page": 1, "limit": 10}


async def alias_test(search: str = Query(alias="q")):
    return {"search": search}


def test_query_alias(test_client_factory):
    with create_client(routes=[Path("/", alias_test)], settings_module=EncoderSettings) as client:
        response = client.get("/?q=python")
        assert response.json() == {"search": "python"}


async def typed_param(page: int = Query(cast=int)):
    return {"page": page}


def test_invalid_query_type(test_client_factory):
    with create_client(routes=[Path("/", typed_param)], settings_module=EncoderSettings) as client:
        response = client.get("/?page=abc")
        assert response.status_code == 422  # Invalid integer


async def first(q: str = Query()):
    return {"from": "first", "q": q}


async def second(q: str = Query()):
    return {"from": "second", "q": q}


def test_multiple_query_param_endpoints(test_client_factory):
    with create_client(
        routes=[Path("/one", first), Path("/two", second)], settings_module=EncoderSettings
    ) as client:
        res1 = client.get("/one?q=test1")
        res2 = client.get("/two?q=test2")
        assert res1.json() == {"from": "first", "q": "test1"}
        assert res2.json() == {"from": "second", "q": "test2"}


async def null_param(q: str | None = Query()):
    return {"q": q}


def test_query_none_default(test_client_factory):
    with create_client(routes=[Path("/", null_param)], settings_module=EncoderSettings) as client:
        response = client.get("/")
        assert response.json() == {"q": None}
