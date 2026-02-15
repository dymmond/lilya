import os
from functools import cached_property
from typing import Annotated
from unittest.mock import patch

import pytest

from lilya.conf.global_settings import Settings
from lilya.protocols.cache import CacheBackend
from tests.settings import AppTestSettings, ORJSONSerializerConfig


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


def test_defaults():
    settings = MySettings()

    assert settings.debug is False
    assert settings.port == 8000
    assert settings.host == "localhost"
    assert settings.timeout == 5.5
    assert settings.optional is None
    assert isinstance(settings.cache_backend, FileBackend)


@patch.dict(
    os.environ,
    {"DEBUG": "true", "PORT": "1234", "HOST": "example.com", "TIMEOUT": "10.1"},
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
        "cache_default_ttl": 300,
        "timezone": "UTC",
        "ptpython_config_file": "~/.config/ptpython/config.py",
        "debug": False,
        "environment": "production",
        "version": settings.version,
        "include_in_schema": True,
        "default_route_pattern": "route_patterns",
        "enforce_return_annotation": False,
        "x_frame_options": None,
        "before_request": None,
        "after_request": None,
        "logging_level": "INFO",
        "enable_openapi": False,
        "infer_body": False,
        "enable_intercept_global_exceptions": False,
        "root_path_in_servers": True,
        "root_path": "",
        "redirect_slashes": True,
        "csrf_token_name": "csrf_token",
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


class CustomSettings(MySettings):
    values: tuple[str] = ("value1", "value2")
    values_dict: dict[str, str] = {"key1": "value1", "key2": "value2"}
    values_list: list[str] = ["item1", "item2"]

    @property
    def custom_property(self) -> str:
        return "custom_value"

    @cached_property
    def cached_property_example(self) -> str:
        return "cached_value"


def test_custom_settings():
    settings = CustomSettings()

    assert settings.values == ("value1", "value2")
    assert settings.values_dict == {"key1": "value1", "key2": "value2"}
    assert settings.values_list == ["item1", "item2"]
    assert settings.custom_property == "custom_value"

    d = settings.dict(include_properties=False)
    assert d["values"] == ("value1", "value2")
    assert d["values_dict"] == {"key1": "value1", "key2": "value2"}
    assert d["values_list"] == ["item1", "item2"]

    d = settings.dict(include_properties=True)
    assert "custom_property" in d
    assert "cached_property_example" in d


def test_tuple_with_properties():
    settings = CustomSettings()

    t = settings.tuple(include_properties=True)
    assert ("custom_property", "custom_value") in t
    assert ("cached_property_example", "cached_value") in t

    t = settings.tuple(include_properties=False)
    assert ("custom_property", "custom_value") not in t
    assert ("cached_property_example", "cached_value") not in t


def test_serializer_config():
    class CustomSettings(AppTestSettings): ...

    settings = CustomSettings()
    assert isinstance(settings.serializer_config, ORJSONSerializerConfig)


class MySetts(AppTestSettings):
    @property
    def test_prop(sell) -> list[str]:
        return ["test_prop"]


class InheritedSettings(MySetts): ...


def test_inherited_settings():
    settings = InheritedSettings()
    assert settings.test_prop == ["test_prop"]


def test_inherited_setting_override_without_reannotation():
    class ParentSettings(Settings):
        custom_name: str = "test"

    class ChildSettings(ParentSettings):
        custom_name = "yes"

    settings = ChildSettings()

    assert settings.custom_name == "yes"
    assert settings.dict()["custom_name"] == "yes"


def test_inherited_type_hints_include_parent_fields():
    class ParentSettings(Settings):
        custom_name: str = "test"

    class ChildSettings(ParentSettings):
        custom_name = "yes"

    assert "custom_name" in ChildSettings.__type_hints__
    assert "debug" in ChildSettings.__type_hints__


@patch.dict(os.environ, {"CUSTOM_NAME": "from_env"})
def test_env_override_for_inherited_field_without_reannotation():
    class ParentSettings(Settings):
        custom_name: str = "test"

    class ChildSettings(ParentSettings):
        custom_name = "yes"

    settings = ChildSettings()

    assert settings.custom_name == "from_env"
