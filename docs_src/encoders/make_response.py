from attrs import define
from msgspec import Struct
from pydantic import BaseModel

from lilya import status
from lilya.apps import Lilya
from lilya.responses import make_response
from lilya.routing import Path


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    name: str
    age: int


@define
class AttrItem:
    name: str
    age: int


def pydantic_response():
    data = User(name="lilya", age=24)
    return make_response(
        data,
        status_code=status.HTTP_200_OK,
    )


def pydantic_response_list():
    data = [User(name="lilya", age=24)]
    return make_response(
        data,
        status_code=status.HTTP_201_CREATED,
        background=...,
        headers=...,
    )


def msgspec_struct():
    return make_response(Item(name="lilya", age=24))


def msgspec_struct_list():
    return make_response(
        [Item(name="lilya", age=24)],
        status_code=...,
    )


def attrs_response():
    return make_response(
        AttrItem(name="lilya", age=24),
        status_code=...,
    )


def attrs_response_list():
    return make_response(
        [AttrItem(name="lilya", age=24)],
        status_code=...,
    )


app = Lilya(
    routes=[
        Path("/pydantic", pydantic_response),
        Path("/pydantic-list", pydantic_response_list),
        Path("/msgspec", msgspec_struct),
        Path("/msgspec-list", pydantic_response_list),
        Path("/attrs", attrs_response),
        Path("/attrs-list", attrs_response_list),
    ]
)
