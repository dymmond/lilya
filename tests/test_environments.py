import os
import typing
from pathlib import Path
from typing import Any, Optional

import pytest
from typing_extensions import assert_type

from lilya.datastructures import URL, Secret
from lilya.environments import EnvironLoader
from lilya.exceptions import EnvironmentError


def test_load_types_string():
    loader = EnvironLoader(
        environ={"VALUE": "some_value", "VALUE_CAST": "some_value"},
    )
    assert_type(loader("VALUE"), str)
    assert_type(loader("VALUE_DEFAULT", default=""), str)
    assert_type(loader("VALUE_CAST", cast=str), str)
    assert_type(loader("VALUE_NONE", default=None), Optional[str])
    assert_type(loader("VALUE_CAST_NONE", cast=str, default=None), Optional[str])
    assert_type(loader("VALUE_CAST_VALUE", cast=str, default=""), str)


def test_load_types_string_ignore_case_false():
    loader = EnvironLoader(
        environ={"VALUE": "some_value", "VALUE_CAST": "some_value"},
        ignore_case=False,
    )
    assert_type(loader("VALUE"), str)
    assert_type(loader("VALUE_DEFAULT", default=""), str)
    assert_type(loader("VALUE_CAST", cast=str), str)
    assert_type(loader("VALUE_NONE", default=None), Optional[str])
    assert_type(loader("VALUE_CAST_NONE", cast=str, default=None), Optional[str])
    assert_type(loader("VALUE_CAST_VALUE", cast=str, default=""), str)


def test_load_types_string_ignore_case_true_raises_error():
    loader = EnvironLoader(
        environ={"VALUE": "some_value", "VALUE_CAST": "some_value"},
        ignore_case=False,
    )
    with pytest.raises(KeyError):
        assert_type(loader("value"), str)

    with pytest.raises(KeyError):
        assert_type(loader("value_cast", cast=str), str)


def test_load_types_string_ignore_case_true_raises_error_via_env_function():
    loader = EnvironLoader(
        environ={"VALUE": "some_value", "VALUE_CAST": "some_value"},
        ignore_case=False,
    )
    with pytest.raises(KeyError):
        assert_type(loader.env("value"), str)

    with pytest.raises(KeyError):
        assert_type(loader.env("value_cast", cast=str), str)


def test_load_types_string_via_env_function():
    loader = EnvironLoader(
        environ={"VALUE": "some_value", "VALUE_CAST": "some_value", "BOOLEAN": "1"},
    )
    assert_type(loader.env("VALUE"), str)
    assert_type(loader.env("VALUE_DEFAULT", default=""), str)
    assert_type(loader.env("VALUE_CAST", cast=str), str)
    assert_type(loader.env("VALUE_NONE", default=None), Optional[str])
    assert_type(loader.env("VALUE_CAST_NONE", cast=str, default=None), Optional[str])
    assert_type(loader.env("VALUE_CAST_VALUE", cast=str, default=""), str)


def test_load_types_boolean():
    loader = EnvironLoader(environ={"BOOLEAN": "1"})

    assert_type(loader("BOOLEAN", cast=bool), bool)
    assert_type(loader("BOOLEAN_DEFAULT", cast=bool, default=False), bool)
    assert_type(loader("BOOLEAN_NONE", cast=bool, default=None), Optional[bool])
    assert_type(loader("BOOLEAN_NONE", cast=bool, default=None), Optional[bool])


def test_load_types_boolean_ignore_case_true_raises_error():
    loader = EnvironLoader(environ={"BOOLEAN": "1"}, ignore_case=False)

    with pytest.raises(KeyError):
        assert_type(loader("boolean"), bool)

    with pytest.raises(KeyError):
        assert_type(loader("boolean_cast", cast=bool), bool)


def test_load_types_boolean_ignore_case_true_raises_error_via_env_function():
    loader = EnvironLoader(environ={"BOOLEAN": "1"}, ignore_case=False)

    with pytest.raises(KeyError):
        assert_type(loader.env("boolean"), bool)

    with pytest.raises(KeyError):
        assert_type(loader.env("boolean_cast", cast=bool), bool)


def test_load_types_boolean_via_env_function():
    loader = EnvironLoader(environ={"BOOLEAN": "1"})

    assert_type(loader.env("BOOLEAN", cast=bool), bool)
    assert_type(loader.env("BOOLEAN_DEFAULT", cast=bool, default=False), bool)
    assert_type(loader.env("BOOLEAN_NONE", cast=bool, default=None), Optional[bool])
    assert_type(loader.env("BOOLEAN_NONE", cast=bool, default=None), Optional[bool])


def test_raises_error() -> None:
    loader = EnvironLoader()

    def cast_to_float(v: Any) -> int:
        return float(v)

    with pytest.raises(ValueError):
        loader("FLOAT_CAST_DEFAULT_STRING", cast=cast_to_float, default="true")
    with pytest.raises(ValueError):
        loader("FLOAT_DEFAULT_STR", cast=int, default="true")


def test_missing_env_file_raises(tmpdir: Path):
    path = os.path.join(tmpdir, ".env")

    with pytest.warns(UserWarning, match=f"EnvironLoader file '{path}' not found."):
        EnvironLoader(env_file=path)


def test_environ():
    loader = EnvironLoader()

    loader.add("TESTING", True)
    loader.add("GONE", "123")
    del loader["GONE"]

    assert loader["TESTING"] is True
    assert "GONE" not in loader

    with pytest.raises(EnvironmentError):
        loader["TESTING"] = "False"

    with pytest.raises(
        EnvironmentError, match="Attempting to delete 'GONE'. Value does not exist."
    ):
        del loader["GONE"]

    loader = EnvironLoader()
    assert list(iter(loader)) == list(iter(os.environ))
    assert len(loader) == len(os.environ)


def test_loader(tmpdir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = os.path.join(tmpdir, ".env")
    with open(path, "w") as file:
        file.write("# Line to ignore\n")
        file.write("API_URL=https://api.example.com/request\n")
        file.write("API_HOST=example.com\n")
        file.write("SECRET_API_KEY=12345\n")
        file.write("IS_ENABLED=0\n")
        file.write("# Line to ignore\n")
        file.write("\n")

    config = EnvironLoader(environ={"DEBUG": "true"}, env_file=path)

    def cast_to_int(v: typing.Any) -> int:
        return int(v)

    DEBUG = config("DEBUG", cast=bool)
    API_URL = config("API_URL", cast=URL)
    API_TRATE_LIMIT = config("API_TRATE_LIMIT", cast=int, default=1000)
    API_HOST = config("API_HOST")
    MAIL_HOSTNAME = config("MAIL_HOSTNAME", default=None)
    SECRET_API_KEY = config("SECRET_API_KEY", cast=Secret)
    UNSET_SECRET = config("UNSET_SECRET", cast=Secret, default=None)
    EMPTY_SECRET = config("EMPTY_SECRET", cast=Secret, default="")

    assert config("IS_ENABLED", cast=bool) is False
    assert config("IS_ENABLED", cast=cast_to_int) == 0
    assert config("DEFAULTED_BOOL", cast=cast_to_int, default=True) == 1

    assert DEBUG is True
    assert API_URL.path == "/request"
    assert API_TRATE_LIMIT == 1000
    assert API_HOST == "example.com"
    assert MAIL_HOSTNAME is None
    assert repr(SECRET_API_KEY) == "Secret('***********')"
    assert str(SECRET_API_KEY) == "12345"
    assert bool(SECRET_API_KEY)
    assert not bool(EMPTY_SECRET)
    assert not bool(UNSET_SECRET)

    with pytest.raises(KeyError):
        config.env("MISSING")

    with pytest.raises(ValueError):
        config.env("DEBUG", cast=int)

    with pytest.raises(ValueError):
        config.env("API_HOST", cast=bool)

    config = EnvironLoader(Path(path))
    API_HOST = config("API_HOST")
    assert API_HOST == "example.com"

    config = EnvironLoader()
    monkeypatch.setenv("LILYA_EXAMPLE_TEST", "123")
    monkeypatch.setenv("IS_ENABLED", "1")
    assert config.env("LILYA_EXAMPLE_TEST", cast=int) == 123
    assert config.env("IS_ENABLED", cast=bool) is True

    monkeypatch.setenv("IS_ENABLED", "2")
    with pytest.raises(ValueError):
        config.env("IS_ENABLED", cast=bool)
