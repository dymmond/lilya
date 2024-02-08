import sys
from collections import deque
from dataclasses import dataclass
from typing import Any

import msgspec
import pytest
from msgspec import Struct
from pydantic import BaseModel

from lilya.encoders import Encoder, register_encoder
from lilya.routing import Path
from lilya.testclient import create_client

if sys.version_info <= (3, 9):  # pragma: no cover
    dont_run = True
else:  # pragma: no cover
    dont_run = False

    class PydanticEncoder(Encoder):

        def is_type(self, value: Any) -> bool:
            return isinstance(value, BaseModel)

        def serialize(self, obj: BaseModel) -> dict[str, Any]:
            return obj.model_dump()

    register_encoder(PydanticEncoder())


class MsgSpecEncoder(Encoder):
    __type__ = Struct

    def serialize(self, obj: Any) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj))


register_encoder(MsgSpecEncoder())


@dataclass
class ResponseData:
    name: str
    age: int


def home() -> ResponseData:
    return ResponseData(name="lilya", age=24)


def test_response_dataclass():
    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


class User(BaseModel):
    name: str
    age: int


def base_model() -> User:
    return User(name="lilya", age=24)


@pytest.mark.skipif(dont_run, reason="Python 3.8 internals")
def test_pydantic_custom_response():
    with create_client(routes=[Path("/", base_model)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


def base_model_list() -> User:
    return [User(name="lilya", age=24)]


@pytest.mark.skipif(dont_run, reason="Python 3.8 internals")
def test_pydantic_custom_response_list():
    with create_client(routes=[Path("/", base_model_list)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


class Item(Struct):
    name: str
    age: int


def base_struct() -> Item:
    return Item(name="lilya", age=24)


def test_msgspec_custom_response():
    with create_client(routes=[Path("/", base_struct)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"name": "lilya", "age": 24}


def base_struct_list() -> Item:
    return [Item(name="lilya", age=24)]


def test_msgspec_custom_response_list():
    with create_client(routes=[Path("/", base_struct_list)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [{"name": "lilya", "age": 24}]


@pytest.mark.parametrize("value", ["1", 2, 2.2, None], ids=["str", "int", "float", "none"])
def test_primitive_responses(value):
    def home():
        return value

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == value


def test_dict_response():
    def home():
        return {"message": "works"}

    with create_client(routes=[Path("/", home)]) as client:
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

    def home():
        return value

    with create_client(routes=[Path("/", home)]) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == [1, 2, 3, 4]
