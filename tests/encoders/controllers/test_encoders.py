from collections import deque
from dataclasses import dataclass

import pytest
from attrs import define
from msgspec import Struct
from pydantic import BaseModel

from lilya.controllers import Controller
from lilya.routing import Path
from lilya.testclient import create_client


@dataclass
class ResponseData:
    name: str
    age: int


class Test(Controller):
    def get(self) -> ResponseData:
        return ResponseData(name="lilya", age=24)


def test_response_dataclass():
    with create_client(routes=[Path("/", Test)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


class User(BaseModel):
    name: str
    age: int


class TestModel(Controller):
    def get(self) -> User:
        return User(name="lilya", age=24)


def test_pydantic_custom_response():
    with create_client(routes=[Path("/", TestModel)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


class TestModelList(Controller):
    def get(self) -> list[User]:
        return [User(name="lilya", age=24)]


def test_pydantic_custom_response_list():
    with create_client(routes=[Path("/", TestModelList)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


class Item(Struct):
    name: str
    age: int


class TestStruct(Controller):
    def get(self):
        return Item(name="lilya", age=24)


def test_msgspec_custom_response():
    with create_client(routes=[Path("/", TestStruct)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


class TestStructList(Controller):
    def get(self):
        return [Item(name="lilya", age=24)]


def test_msgspec_custom_response_list():
    with create_client(routes=[Path("/", TestStructList)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


@define
class AttrItem:
    name: str
    age: int


class TestAttr(Controller):
    def get(self):
        return AttrItem(name="lilya", age=24)


def test_attrs_custom_response():
    with create_client(routes=[Path("/", TestAttr)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


class TestAttrList(Controller):
    def get(self):
        return [AttrItem(name="lilya", age=24)]


def test_attrs_custom_response_list():
    with create_client(routes=[Path("/", TestAttrList)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


@pytest.mark.parametrize("value", ["1", 2, 2.2, None], ids=["str", "int", "float", "none"])
def test_primitive_responses(value):
    class Test(Controller):
        def get(self):
            return value

    with create_client(routes=[Path("/", Test)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == value


def test_dict_response():
    class Test(Controller):
        def get(self):
            return {"message": "works"}

    with create_client(routes=[Path("/", Test)]) as client:
        response = client.get("/")

        assert response.status_code == 200
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
    class Test(Controller):
        def get(self):
            return value

    with create_client(routes=[Path("/", Test)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [1, 2, 3, 4]
