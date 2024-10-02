from __future__ import annotations

from collections import deque
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from typing import Any, Generic, TypeVar, cast

from lilya._utils import is_class_and_subclass

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


ENCODER_TYPES: deque[Encoder] = deque(
    [
        DataclassEncoder(),
        EnumEncoder(),
        PurePathEncoder(),
        PrimitiveEncoder(),
        DictEncoder(),
        StructureEncoder(),
    ]
)


def register_encoder(encoder: Encoder[Any] | type[Encoder[Any]]) -> None:
    if is_class_and_subclass(encoder, Encoder):
        encoder = encoder()  # type: ignore
    remove_elements: list[Encoder] = []
    for value in ENCODER_TYPES:
        if value.__class__ == encoder.__class__:
            remove_elements.append(value)
    for element in remove_elements:
        ENCODER_TYPES.remove(element)
    ENCODER_TYPES.appendleft(cast(Encoder[Any], encoder))


def json_encoder(value: Any) -> Any:
    """
    Encode a value to a JSON-compatible format using a list of encoder types.

    Parameters:
    value (Any): The value to encode.

    Returns:
    Any: The JSON-compatible encoded value.

    Raises:
    ValueError: If the value is not serializable by any provided encoder type.
    """

    for encoder in ENCODER_TYPES:
        if encoder.is_type(value):
            return encoder.serialize(value)

    # If no encoder was found, raise a ValueError
    raise ValueError(f"Object of type '{type(value).__name__}' is not JSON serializable.")
