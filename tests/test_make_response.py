import datetime
from collections import deque
from dataclasses import dataclass

import orjson
import pytest
from attrs import define
from msgspec import Struct
from pydantic import BaseModel

from lilya.encoders import Encoder, apply_structure
from lilya.responses import Response, make_response
from lilya.routing import Path
from lilya.testclient import create_client


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
def test_response_dataclass(json_encode_kwargs):
    @dataclass
    class ResponseData:
        name: str
        age: int

    def home() -> ResponseData:
        data = ResponseData(name="lilya", age=24)
        return make_response(data, status_code=201, json_encode_extra_kwargs=json_encode_kwargs)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"name": "lilya", "age": 24}


class User(BaseModel):
    name: str
    age: int


def base_model() -> User:
    data = User(name="lilya", age=24)
    return make_response(data, status_code=208)


def test_pydantic_custom_make_response():
    with create_client(routes=[Path("/", base_model)]) as client:
        response = client.get("/")

        assert response.status_code == 208
        assert response.json() == {"name": "lilya", "age": 24}


def base_model_list() -> User:
    data = [User(name="lilya", age=24)]
    return make_response(data)


def test_pydantic_custom_make_response_list():
    with create_client(routes=[Path("/", base_model_list)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


class Item(Struct):
    name: str
    age: int


def base_struct():
    data = Item(name="lilya", age=24)
    return make_response(data, status_code=201)


def test_msgspec_custom_make_response():
    with create_client(routes=[Path("/", base_struct)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"name": "lilya", "age": 24}


def base_struct_list():
    data = [Item(name="lilya", age=24)]
    return make_response(data, status_code=208)


def test_msgspec_custom_make_response_list():
    with create_client(routes=[Path("/", base_struct_list)]) as client:
        response = client.get("/")

        assert response.status_code == 208
        assert response.json() == [{"name": "lilya", "age": 24}]


@define
class AttrItem:
    name: str
    age: int


def base_attrs():
    data = AttrItem(name="lilya", age=24)
    return make_response(data)


def test_attrs_custom_make_response():
    with create_client(routes=[Path("/", base_attrs)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


def base_attrs_list():
    data = [AttrItem(name="lilya", age=24)]
    return make_response(data)


def test_attrs_custom_make_response_list():
    with create_client(routes=[Path("/", base_attrs_list)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
@pytest.mark.parametrize("value", ["hello", 2, 2.2, None], ids=["str", "int", "float", "none"])
def test_primitive_responses(value, json_encode_kwargs):
    def home():
        return make_response(value, status_code=201, json_encode_extra_kwargs=json_encode_kwargs)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == value


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
@pytest.mark.parametrize(
    "value,result",
    [
        ("hello", "hello"),
        (b"hello", "hello"),
        (2, "2"),
        (2.2, "2.2"),
        (None, ""),
        (datetime.datetime(2014, 11, 10), "2014-11-10T00:00:00"),
    ],
    ids=["str", "bytes", "int", "float", "none", "datetime"],
)
def test_classic_response(value, result, json_encode_kwargs):
    def home():
        return make_response(value, status_code=201, response_class=Response)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.text == result


def test_dict_response():
    def home():
        return make_response({"message": "works"}, status_code=201)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"message": "works"}


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
@pytest.mark.parametrize(
    "value",
    [
        [1, 2, 3, 4],
        {1, 2, 3, 4},
        frozenset({1, 2, 3, 4}),
        (1, 2, 3, 4),
        deque([1, 2, 3, 4]),
    ],
    ids=["list", "set", "frozenset", "tuple", "deque"],
)
def test_structure_responses(value, json_encode_kwargs):
    def home():
        return make_response(value, status_code=201, json_encode_extra_kwargs=json_encode_kwargs)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == [1, 2, 3, 4]


def test_custom_encoder_response():
    class Foo:
        a: int

        def __init__(self, a: int):
            self.a = a

        def __eq__(self, other) -> bool:
            return isinstance(other, type(self)) and other.a == self.a

    @dataclass
    class FooDataclass:
        a: int

    class FooEncoder(Encoder):
        __type__ = Foo

        def serialize(self, value: Foo) -> dict:
            return {"a": value.a}

        def encode(self, structure, value):
            foo = Foo(value["a"])
            return foo

    def home():
        return make_response(Foo(a=3), status_code=201, encoders=[FooEncoder()])

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"a": 3}
        result = apply_structure(Foo, response.json(), with_encoders=[FooEncoder()])
        assert result == Foo(3)
        assert result != FooDataclass(3)
        # try again with defaults and a similar structured dataclass
        assert apply_structure(FooDataclass, response.json()) == FooDataclass(3)


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
def test_custom_molding_only_encoder_response(json_encode_kwargs):
    class Foo:
        a: int

        def __init__(self, a: int):
            self.a = a

        def __eq__(self, other) -> bool:
            return isinstance(other, type(self)) and other.a == self.a

    class FooEncoder(Encoder):
        __type__ = Foo

        def encode(self, structure, value):
            foo = Foo(value["a"])
            return foo

    def home():
        return make_response(
            {"a": 3},
            status_code=201,
            encoders=[FooEncoder()],
            json_encode_extra_kwargs=json_encode_kwargs,
        )

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"a": 3}
        result = apply_structure(Foo, response.json(), with_encoders=[FooEncoder()])
        assert result == Foo(3)
