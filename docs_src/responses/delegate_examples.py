from lilya.apps import Lilya
from lilya.routing import Path


def home_dict():
    return {"message": "Welcome home"}


def home_frozen_set():
    return frozenset({"message": "Welcome home"})


def home_set():
    return set({"message": "Welcome home"})


def home_list():
    return ["Welcome", "home"]


def home_str():
    return "Welcome home"


def home_int():
    return 1


def home_float():
    return 2.0


app = Lilya(
    routes=[
        Path("/dict", home_dict),
        Path("/fronzenset", home_frozen_set),
        Path("/set", home_set),
        Path("/list", home_list),
        Path("/str", home_str),
        Path("/int", home_int),
        Path("/float", home_float),
    ]
)
