from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Dict, Generic, TypeVar

T = TypeVar("T")

# path_regex = re.compile(r"{(.*?)}")
path_regex = re.compile(r"{([^:]+):([^}]+)}")


@dataclass
class Transformer(Generic[T]):
    """
    Base for all path transformers
    of lilya. Dataclasses are used
    for the simplicity of the syntax
    """

    regex: ClassVar[str] = ""

    def transform(self, value: str) -> T:
        raise NotImplementedError()  # pragma: no cover

    def normalise(self, value: T) -> str:  # pragma: no cover
        raise NotImplementedError()  # pragma: no cover


@dataclass
class StringConvertor(Transformer[str]):
    regex = "[^/]+"

    def transform(self, value: str) -> str:
        return value

    def normalise(self, value: str) -> str:
        value = str(value)
        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


@dataclass
class PathConvertor(Transformer[str]):
    regex = ".*"

    def transform(self, value: str) -> str:
        return str(value)

    def normalise(self, value: str) -> str:
        return str(value)


@dataclass
class IntegerConvertor(Transformer[int]):
    regex = "[0-9]+"

    def transform(self, value: str) -> int:
        return int(value)

    def normalise(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "Negative integers are not supported"
        return str(value)


@dataclass
class FloatConvertor(Transformer[float]):
    regex = r"[0-9]+(\.[0-9]+)?"

    def transform(self, value: str) -> float:
        return float(value)

    def normalise(self, value: float) -> str:
        value = float(value)
        assert value >= 0.0, "Negative floats are not supported"
        assert not math.isnan(value), "NaN values are not supported"
        assert not math.isinf(value), "Infinite values are not supported"
        return ("%0.20f" % value).rstrip("0").rstrip(".")


@dataclass
class UUIDConvertor(Transformer[uuid.UUID]):
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def transform(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    def normalise(self, value: uuid.UUID) -> str:
        return str(value)


@dataclass
class DatetimeConvertor(Transformer[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

    def transform(self, value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    def normalise(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")


# Available converter types
CONVERTOR_TYPES: Dict[str, Transformer] = {
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
    "datetime": DatetimeConvertor(),
}
