import os
from typing import Annotated
from unittest.mock import patch

import pytest

from lilya.conf.global_settings import Settings  # Replace with actual import
from lilya.protocols.cache import CacheBackend


class FileBackend(CacheBackend):
    def get(self, key: str):
        return None

    def set(self, key: str, value: str): ...

    def delete(self, key: str): ...

    def clear(self): ...


class MySettings(Settings):
    debug: Annotated[bool, "Enable debug mode"] = False
    port: Annotated[int, "Port to bind"] = 8000
    host: str = "localhost"
    timeout: float = 5.5
    optional: str | None = None
    cache_backend: CacheBackend = FileBackend()


# --- Initialization Tests ---


def test_defaults():
    settings = MySettings()

    assert settings.debug is False
    assert settings.port == 8000
    assert settings.host == "localhost"
    assert settings.timeout == 5.5
    assert settings.optional is None
    assert isinstance(settings.cache_backend, FileBackend)


@patch.dict(
    os.environ, {"DEBUG": "true", "PORT": "1234", "HOST": "example.com", "TIMEOUT": "10.1"}
)
def test_env_override():
    settings = MySettings()
    assert settings.debug is True
    assert settings.port == 1234
    assert settings.host == "example.com"
    assert settings.timeout == 10.1


@patch.dict(os.environ, {"DEBUG": "yes"})
def test_bool_casting():
    settings = MySettings()
    assert settings.debug is True


@patch.dict(os.environ, {"PORT": "not_an_int"})
def test_invalid_cast():
    with pytest.raises(ValueError):
        MySettings()


def test_dict_default():
    settings = MySettings()
    d = settings.dict(exclude={"cache_backend"})

    assert d == {
        "debug": False,
        "port": 8000,
        "host": "localhost",
        "timeout": 5.5,
        "optional": None,
    }


def test_dict_upper():
    settings = MySettings()
    d = settings.dict(upper=True)

    assert "DEBUG" in d and "debug" not in d


def test_dict_exclude_none():
    settings = MySettings()
    d = settings.dict(exclude_none=True)
    assert "optional" not in d


def test_dict_upper_exclude_none():
    settings = MySettings()
    d = settings.dict(exclude_none=True, upper=True)

    assert "OPTIONAL" not in d
    assert "DEBUG" in d


def test_tuple_default():
    settings = MySettings()
    t = settings.tuple()

    assert ("debug", False) in t


def test_tuple_upper():
    settings = MySettings()
    t = settings.tuple(upper=True)

    assert ("DEBUG", False) in t


def test_tuple_exclude_none():
    settings = MySettings()
    t = settings.tuple(exclude_none=True)

    assert not any(k == "optional" for k, _ in t)


def test_tuple_upper_exclude_none():
    settings = MySettings()
    t = settings.tuple(exclude_none=True, upper=True)

    assert not any(k == "OPTIONAL" for k, _ in t)


@patch.dict(os.environ, {"DEBUG": "1"})
def test_annotated_bool():
    settings = MySettings()

    assert settings.debug is True


@patch.dict(os.environ, {"PORT": "9000"})
def test_annotated_int():
    settings = MySettings()

    assert settings.port == 9000


@patch.dict(os.environ, {"OPTIONAL": "hello"})
def test_optional_field():
    settings = MySettings()

    assert settings.optional == "hello"


def test_missing_env_var_uses_default():
    settings = MySettings()

    assert settings.port == 8000


@patch.dict(os.environ, {"TIMEOUT": "invalid"})
def test_invalid_float_cast():
    with pytest.raises(ValueError):
        MySettings()


def test_dict_keys_are_strings():
    settings = MySettings()

    assert all(isinstance(k, str) for k in settings.dict().keys())
