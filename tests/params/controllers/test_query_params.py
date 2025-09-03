import pytest
from pydantic import BaseModel

from lilya.controllers import Controller
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


class QueryParamControllerBool(Controller):
    async def get(self, name: str, by_me: int = Query(cast=bool)):
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
        routes=[Path("/{name}", QueryParamControllerBool)], settings_module=EncoderSettings
    ) as client:
        response = client.get(f"/lilya?by_me={value}")

        assert response.json() == {"name": "lilya", "search": expected}


class QueryParamController(Controller):
    async def get(self, name: str, q: str = Query()):
        return {"name": name, "search": q}


def test_inject_query_params(test_client_factory):
    with create_client(
        routes=[Path("/{name}", QueryParamController)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya?q=result")

        assert response.json() == {"name": "lilya", "search": "result"}


class QueryParamControllerModel(Controller):
    async def get(self, user: User, name: str, q=Query()):
        return {"user": user.model_dump(), "name": name, "search": q}


def test_with_models(test_client_factory):
    data = {"name": "lilya", "age": 2}

    with create_client(
        routes=[Path("/{name}", QueryParamControllerModel)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/lilya", json=data)
        assert response.json() == {
            "user": {"name": "lilya", "age": 2},
            "name": "lilya",
            "search": None,
        }


class QueryParamSimple(Controller):
    async def get(self, name: str = Query(), q: str = Query()):
        return {"name": name, "search": q}


def test_inject_query_params_simple(test_client_factory):
    with create_client(
        routes=[Path("/", QueryParamSimple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/?name=lilya&q=result")

        assert response.json() == {"name": "lilya", "search": "result"}


class QueryParamControllerSimple(Controller):
    async def get(self, name: str = Query(), q: str = Query()):
        return {"name": name, "search": q}


def test_inject_query_params_simpler(test_client_factory):
    with create_client(
        routes=[Path("/", QueryParamControllerSimple)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/?q=result")

        assert response.json() == {"name": None, "search": "result"}


class QueryParamModelWithInject(Controller):
    async def get(self, user: User, name: str, service: Dummy, q=Query()):
        return {"user": user.model_dump(), "service": service.show(), "name": name, "search": q}


def test_with_models_with_inject(test_client_factory):
    data = {"name": "lilya", "age": 2}

    with create_client(
        routes=[
            Path("/{name}", QueryParamModelWithInject, dependencies={"service": Provide(Dummy)})
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


class RequiredParam(Controller):
    async def get(self, q: str = Query(required=True)):
        return {"q": q}


def test_required_query_param_missing(test_client_factory):
    with create_client(
        routes=[Path("/", RequiredParam)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")

        assert response.status_code == 422


class DefaultQuery(Controller):
    async def get(self, page: int = Query(default=1), limit: int = Query(default=10)):
        return {"page": page, "limit": limit}


def test_query_defaults(test_client_factory):
    with create_client(
        routes=[Path("/", DefaultQuery)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.json() == {"page": 1, "limit": 10}


class AliasController(Controller):
    async def get(self, search: str = Query(alias="q")):
        return {"search": search}


class TypedController(Controller):
    async def get(self, page: int = Query(cast=int)):
        return {"page": page}


def test_invalid_query_type(test_client_factory):
    with create_client(
        routes=[Path("/", TypedController)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/?page=abc")
        assert response.status_code == 422  # Invalid integer


class First(Controller):
    async def get(self, q: str = Query()):
        return {"from": "first", "q": q}


class Second(Controller):
    async def get(self, q: str = Query()):
        return {"from": "second", "q": q}


def test_multiple_query_param_endpoints(test_client_factory):
    with create_client(
        routes=[Path("/one", First), Path("/two", Second)], settings_module=EncoderSettings
    ) as client:
        res1 = client.get("/one?q=test1")
        res2 = client.get("/two?q=test2")
        assert res1.json() == {"from": "first", "q": "test1"}
        assert res2.json() == {"from": "second", "q": "test2"}


class NullController(Controller):
    async def get(self, q: str | None = Query()):
        return {"q": q}


def test_query_none_default(test_client_factory):
    with create_client(
        routes=[Path("/", NullController)], settings_module=EncoderSettings
    ) as client:
        response = client.get("/")
        assert response.json() == {"q": None}


def test_parse_bool_true(test_client_factory):
    class BoolController(Controller):
        async def get(
            self, flag: Query = Query(default=True, cast=bool, description="A boolean flag")
        ):
            return {"flag": flag}

    with create_client(routes=[Path("/", BoolController)]) as client:
        response = client.get("/?flag=true")
        assert response.json() == {"flag": True}

        response = client.get("/?flag=false")
        assert response.json() == {"flag": False}

        response = client.get("/")
        assert response.json() == {"flag": True}


def test_parse_bool_false(test_client_factory):
    class BoolController(Controller):
        async def get(
            self, flag: Query = Query(default=False, cast=bool, description="A boolean flag")
        ):
            return {"flag": flag}

    with create_client(routes=[Path("/", BoolController)]) as client:
        response = client.get("/?flag=true")
        assert response.json() == {"flag": True}

        response = client.get("/?flag=false")
        assert response.json() == {"flag": False}

        response = client.get("/")
        assert response.json() == {"flag": False}
