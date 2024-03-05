from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

T = TypeVar("T")

# path_regex = re.compile(r"{(.*?)}")
path_regex = re.compile(r"{([^:]+):([^}]+)}")


@dataclass(frozen=True, eq=True)
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


@dataclass(frozen=True, eq=True)
class StringTransformer(Transformer[str]):
    regex = "[^/]+"

    def transform(self, value: str) -> str:
        return value

    def normalise(self, value: str) -> str:
        value = str(value)
        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


@dataclass(frozen=True, eq=True)
class PathTransformer(Transformer[str]):
    regex = ".*"

    def transform(self, value: str) -> str:
        return str(value)

    def normalise(self, value: str) -> str:
        return str(value)


@dataclass(frozen=True, eq=True)
class IntegerTransformer(Transformer[int]):
    regex = "[0-9]+"

    def transform(self, value: str) -> int:
        return int(value)

    def normalise(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "Negative integers are not supported"
        return str(value)


@dataclass(frozen=True, eq=True)
class FloatTransformer(Transformer[float]):
    regex = r"[0-9]+(\.[0-9]+)?"

    def transform(self, value: str) -> float:
        return float(value)

    def normalise(self, value: float) -> str:
        value = float(value)
        assert value >= 0.0, "Negative floats are not supported"
        assert not math.isnan(value), "NaN values are not supported"
        assert not math.isinf(value), "Infinite values are not supported"
        return ("%0.20f" % value).rstrip("0").rstrip(".")


@dataclass(frozen=True, eq=True)
class UUIDTransformer(Transformer[uuid.UUID]):
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def transform(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    def normalise(self, value: uuid.UUID) -> str:
        return str(value)


@dataclass(frozen=True, eq=True)
class DatetimeTransformer(Transformer[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

    def transform(self, value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    def normalise(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")


# Available converter types
TRANSFORMER_TYPES: dict[str, Transformer] = {
    "str": StringTransformer(),
    "path": PathTransformer(),
    "int": IntegerTransformer(),
    "float": FloatTransformer(),
    "uuid": UUIDTransformer(),
    "datetime": DatetimeTransformer(),
}

TRANSFORMER_PYTHON_TYPES = {v.__class__.__name__: k for k, v in TRANSFORMER_TYPES.items()}


def register_path_transformer(key: str, transformer: Transformer[Any]) -> None:
    """
    Adds custom transformers to the already known dictionary of path
    transformers.
    """
    TRANSFORMER_TYPES[key] = transformer
    TRANSFORMER_PYTHON_TYPES[transformer.__class__.__name__] = key
