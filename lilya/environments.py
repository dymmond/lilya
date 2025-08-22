from __future__ import annotations

import inspect
import os
import warnings
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, TypeVar, cast as tcast

from multidict import MultiDict

from lilya.exceptions import EnvError
from lilya.types import Empty

Cast = Callable[..., Any]

T = TypeVar("T")


class BooleanParser:
    def __init__(self, key: str, value: Any) -> None:
        self._value = value
        self._key = key
        self._boolean_mapping: dict[str, bool] = {
            "true": True,
            "1": True,
            "y": True,
            "false": False,
            "0": False,
            "n": False,
        }

    def __validate__(self) -> bool:
        value = self._value.lower()
        return value in self._boolean_mapping

    def __cast__(self) -> Any:
        is_valid: bool = self.__validate__()
        if not is_valid:
            raise ValueError(
                f"EnvironLoader '{self._key}' has the value '{self._value} but it is not a valid boolean."
            )
        return self._boolean_mapping[self._value]

    def __call__(self) -> Any:
        return self.__cast__()


class EnvironLoader(MultiDict):
    """
    Object responsible for loading the environment
    variables and cast them into specific formats.
    """

    def __init__(
        self,
        env_file: str | Path | None = None,
        environ: MultiDict | None = None,
        prefix: str | None = None,
        ignore_case: bool = False,
    ) -> None:
        if not ignore_case and environ is not None:
            environ = tcast(MultiDict, {k.upper(): v for k, v in environ.items()})

        self.__env__: MultiDict = environ if environ is not None else tcast(MultiDict, os.environ)
        super().__init__(self.__env__)
        self.__read__: set[str] = set()
        self._env_file = env_file
        self._prefix = "" if prefix is None else prefix
        self._env_file_values: dict[str, str] = {}

        if self._env_file is not None:
            if not os.path.isfile(env_file):
                warnings.warn(f"EnvironLoader file '{self._env_file}' not found.", stacklevel=2)
            else:
                self._env_file_values = self._get_enviroment_file_values(env_file)

    def __getitem__(self, __key: str) -> str:
        self.__read__.add(__key)
        return tcast(str, self.getone(__key))

    def __setitem__(self, __key: str, __value: str) -> None:
        if __key in self.__read__:
            raise EnvError(
                f"Cannot set environment variable '{__key}'. Value has already been read."
            )
        self.update(__key=__value)

    def __delitem__(self, __key: str) -> None:
        if __key in self.__read__:
            raise EnvError(
                f"Cannot delete environment variable '{__key}'. Value has already been read."
            )

        try:
            super().__delitem__(__key)
        except KeyError:
            raise EnvError(f"Attempting to delete '{__key}'. Value does not exist.") from None

    def multi_items(self) -> Generator[tuple[str, T], None, None]:
        """Get all keys and values, including duplicates."""
        for key in set(self):
            for value in self.getall(key):
                yield key, value

    def get_multi_items(self) -> list[Any]:
        """
        Returns a list of values from the multi items
        """
        return list(self.multi_items())

    def __call__(self, key: str, cast: Cast | None = None, default: Any = Empty) -> Any:
        return self.env(key=key, cast=cast, default=default)

    def _get_enviroment_file_values(self, env_file: str | Path) -> dict[str, str]:
        """
        Reads a given environment variable file.
        """
        values: dict[str, str] = {}
        with open(env_file) as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = map(str.strip, line.split("=", 1))
                    values[key] = value.strip("\"'")
        return values

    def __cast__(self, key: str, value: str, cast: Cast) -> Any:
        if inspect.isfunction(cast):
            return cast(value)
        if not cast or not value:
            return value
        elif cast is bool and isinstance(value, str):
            parser = BooleanParser(key, value)
            return parser()
        try:
            return cast(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"EnvironLoader '{key} has value '{value}' but it is not a valid {cast.__name__}"
            ) from None

    def env(self, key: str, cast: Cast | None = None, default: Any = Empty) -> Any:
        key = self._prefix + key
        if key in self.keys():
            value = self.getone(key)
            return self.__cast__(key, value, cast)
        if key in self.__env__:
            value = self.__env__.get(key)
            return self.__cast__(key, value, cast)
        if key in self._env_file_values:
            value = self._env_file_values[key]
            return self.__cast__(key, value, cast)
        if default is not Empty:
            return self.__cast__(key, default, cast)
        raise KeyError(f"EnvironLoader '{key}' cannot be found and not default was provided.")
