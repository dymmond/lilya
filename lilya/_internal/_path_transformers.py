from __future__ import annotations

import math
import re
import typing
import uuid
from datetime import date, datetime
from typing import Dict, Generic, TypeVar

T = TypeVar("T")

# path_regex = re.compile(r"{(.*?)}")
path_regex = re.compile(r"{([^:]+):([^}]+)}")


class PathTransformer(Generic[T]):
    regex: typing.ClassVar[str] = ""

    def render(self, value: str) -> T:
        raise NotImplementedError()  # pragma: no cover

    def to_string(self, value: T) -> str:
        raise NotImplementedError()  # pragma: no cover


class StringConvertor(PathTransformer[str]):
    regex = "[^/]+"

    def render(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        value = str(value)
        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


class PathConvertor(PathTransformer[str]):
    regex = ".*"

    def render(self, value: str) -> str:
        return str(value)

    def to_string(self, value: str) -> str:
        return str(value)


class IntegerConvertor(PathTransformer[int]):
    regex = "[0-9]+"

    def render(self, value: str) -> int:
        return int(value)

    def to_string(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "Negative integers are not supported"
        return str(value)


class FloatConvertor(PathTransformer[float]):
    regex = r"[0-9]+(\.[0-9]+)?"

    def render(self, value: str) -> float:
        return float(value)

    def to_string(self, value: float) -> str:
        value = float(value)
        assert value >= 0.0, "Negative floats are not supported"
        assert not math.isnan(value), "NaN values are not supported"
        assert not math.isinf(value), "Infinite values are not supported"
        return ("%0.20f" % value).rstrip("0").rstrip(".")


class UUIDConvertor(PathTransformer[uuid.UUID]):
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def render(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    def to_string(self, value: uuid.UUID) -> str:
        return str(value)


class DatetimeConvertor(PathTransformer[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

    def render(self, value: str) -> str:
        return datetime.strftime(value, "%Y-%m-%dT%H:%M:%S")

    def to_string(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")


class DateConvertor(PathTransformer[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}?"

    def render(self, value: str) -> datetime:
        return datetime.strftime(value, "%Y-%m-%d")

    def to_string(self, value: date) -> str:
        return value.strftime("%Y-%m-%d")


# Available converter types
CONVERTOR_TYPES: Dict[str, PathTransformer] = {
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
    "datetime": DatetimeConvertor(),
    "date": DateConvertor(),
}
