from attrs import define
from msgspec import Struct
from pydantic import BaseModel

from lilya.app import Lilya
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
    return User(name="lilya", age=24)


def pydantic_response_list():
    return [User(name="lilya", age=24)]


def msgspec_struct():
    return Item(name="lilya", age=24)


def msgspec_struct_list():
    return [Item(name="lilya", age=24)]


def attrs_response():
    return AttrItem(name="lilya", age=24)


def attrs_response_list():
    return [AttrItem(name="lilya", age=24)]


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
