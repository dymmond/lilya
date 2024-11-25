from collections import deque
from dataclasses import dataclass

import pytest
from attrs import define
from msgspec import Struct
from pydantic import BaseModel

from lilya.responses import make_response
from lilya.routing import Path
from lilya.testclient import create_client


@dataclass
class ResponseData:
    name: str
    age: int


def home() -> ResponseData:
    data = ResponseData(name="lilya", age=24)
    return make_response(data, status_code=201)


def test_response_dataclass():
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


@pytest.mark.parametrize("value", ["1", 2, 2.2, None], ids=["str", "int", "float", "none"])
def test_primitive_responses(value):
    def home():
        return make_response(value, status_code=201)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == value


def test_dict_response():
    def home():
        return make_response({"message": "works"}, status_code=201)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == {"message": "works"}


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
def test_structure_responses(value):
    def home():
        return make_response(value, status_code=201)

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 201
        assert response.json() == [1, 2, 3, 4]
