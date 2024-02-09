from __future__ import annotations

from collections import deque
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


class Encoder(Generic[T]):
    """
    The base class for any custom encoder
    added to the system.
    """

    __type__: Any | None = None

    def is_type(self, value: Any) -> bool:
        return isinstance(value, self.__type__)

    def serialize(self, obj: T) -> T:
        raise NotImplementedError()


class DataclassEncoder(Encoder[Any]):

    def is_type(self, value: Any) -> bool:
        return cast(bool, is_dataclass(value))

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)


class EnumEncoder(Encoder[Enum]):
    __type__ = Enum

    def serialize(self, obj: T) -> Any:
        return obj.value


class PurePathEncoder(Encoder[Any]):
    __type__ = PurePath

    def serialize(self, obj: PurePath) -> str:
        return str(obj)


class PrimitiveEncoder(Encoder[Any]):
    __type__ = (str, int, float, type(None))

    def serialize(self, obj: Any) -> Any:
        return obj


class DictEncoder(Encoder[dict]):
    __type__ = dict

    def serialize(self, obj: dict) -> dict:
        return obj


class StructureEncoder(Encoder[Any]):
    __type__ = (list, set, frozenset, GeneratorType, tuple, deque)

    def serialize(self, obj: Any) -> Any:
        serialized_objects = []
        for item in obj:
            for encoder in ENCODER_TYPES:
                if not encoder.is_type(item):
                    continue
                serialized_objects.append(encoder.serialize(item))
        return serialized_objects


ENCODER_TYPES: set[Encoder] = {
    DataclassEncoder(),
    EnumEncoder(),
    PurePathEncoder(),
    PrimitiveEncoder(),
    DictEncoder(),
    StructureEncoder(),
}


def register_encoder(encoder: Encoder[Any]) -> None:
    ENCODER_TYPES.add(encoder)


def json_encoder(value: Any) -> Any:
    result: Any = None

    for encoder in ENCODER_TYPES:
        try:
            if not encoder.is_type(value):
                continue
            result = encoder.serialize(value)
            break
        except (TypeError, AttributeError):
            continue

    if result is None:
        raise ValueError(f"object of type {type(value)} is not json serializable.")

    return result
