from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Generator, Iterable, Sequence
from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from inspect import isclass
from pathlib import PurePath
from typing import Any, Protocol, TypeVar, cast, runtime_checkable

T = TypeVar("T")


# TODO: timedelta encode
@runtime_checkable
class EncoderProtocol(Protocol[T]):
    def is_type(self, value: Any) -> bool:
        """Check if encoder is applicable for this type"""

    def serialize(self, value: T) -> Any:
        """ "Prepare for serialization."""


# not runtime-checkable
class WithEncodeProtocol(Protocol):
    def is_type_structure(self, value: Any) -> bool:
        """Check if encoder is applicable for this type"""

    def encode(self, structure: Any, value: Any) -> Any:
        """
        Function that transforms a value into the structure
        """


class Encoder(EncoderProtocol[T]):
    """
    The base class for any custom encoder
    added to the system.
    """

    name: str | None = None
    __type__: type | tuple[type, ...] | None = None

    def is_type(self, value: Any) -> bool:
        return isinstance(value, self.__type__)

    def is_type_structure(self, value: Any) -> bool:
        return issubclass(value, self.__type__)


class DataclassEncoder(EncoderProtocol, WithEncodeProtocol):
    name: str = "DataclassEncoder"

    def is_type(self, value: Any) -> bool:
        return cast(bool, is_dataclass(value))

    is_type_structure = is_type

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)

    def encode(self, structure: Any, value: Any) -> Any:
        return structure(**value)


class NamedTupleEncoder(EncoderProtocol, WithEncodeProtocol):
    name: str = "NamedTupleEncoder"

    def is_type(self, value: Any) -> bool:
        return isinstance(value, tuple) and hasattr(value, "_asdict")

    def is_type_structure(self, value: Any) -> bool:
        return issubclass(value, tuple) and hasattr(value, "_asdict")

    def serialize(self, obj: Any) -> dict:
        return cast(dict, obj._asdict())

    def encode(self, structure: type[Any], obj: Any) -> Any:
        if isinstance(obj, dict):
            return structure(**obj)
        return structure(*obj)


class ModelDumpEncoder(EncoderProtocol, WithEncodeProtocol):
    name: str = "ModelDumpEncoder"
    # e.g. pydantic

    def is_type(self, value: Any) -> bool:
        return hasattr(value, "model_dump")

    is_type_structure = is_type

    def serialize(self, value: Any) -> Any:
        return value.model_dump()

    def encode(self, structure: type, value: Any) -> Any:
        return structure(**value)


class EnumEncoder(Encoder[Enum], WithEncodeProtocol):
    name: str = "EnumEncoder"
    __type__ = Enum

    def serialize(self, obj: Enum) -> Any:
        return obj.value

    def encode(self, structure: type[Enum], value: Any) -> Enum:
        return structure(value)


class PurePathEncoder(Encoder[Any], WithEncodeProtocol):
    name: str = "PurePathEncoder"
    __type__ = PurePath

    def serialize(self, obj: PurePath) -> str:
        return str(obj)

    def encode(self, structure: type[PurePath], value: Any) -> PurePath:
        return structure(value)


class DateEncoder(Encoder[Any], WithEncodeProtocol):
    name: str = "DateEncoder"
    __type__ = date

    def serialize(self, obj: date) -> str:
        return obj.isoformat()

    def encode(self, structure: type[date], value: Any) -> date | datetime:
        date_obj = datetime.fromisoformat(value)
        if issubclass(structure, datetime):
            return date_obj
        return date_obj.date()


class StructureEncoder(Encoder, WithEncodeProtocol):
    name: str
    __type__ = (set, frozenset, Generator, Iterable, deque)

    def serialize(self, obj: Any) -> list:
        return list(cast(Any, obj))

    def encode(self, structure: type, obj: Any) -> list:
        return list(obj)


DEFAULT_ENCODER_TYPES: deque[EncoderProtocol] = deque(
    (
        DataclassEncoder(),
        NamedTupleEncoder(),
        ModelDumpEncoder(),
        EnumEncoder(),
        PurePathEncoder(),
        DateEncoder(),
        StructureEncoder(),
    )
)

ENCODER_TYPES: ContextVar[Sequence[EncoderProtocol]] = ContextVar(
    "ENCODER_TYPES", default=DEFAULT_ENCODER_TYPES
)


def get_encoder_name(encoder: EncoderProtocol) -> str:
    if getattr(encoder, "name", None):
        return cast(str, encoder.name)
    else:
        return type(encoder).__name__


def register_encoder(encoder: EncoderProtocol | type[EncoderProtocol]) -> None:
    if isclass(encoder):
        encoder = encoder()
    if not isinstance(encoder, EncoderProtocol):
        raise RuntimeError(f'"{encoder}" is not implementing the EncoderProtocol.')

    encoder_types = ENCODER_TYPES.get()
    if not isinstance(encoder_types, deque):
        raise TypeError(
            'For registering a new encoder a "deque" is required as set "ENCODER_TYPES" value.'
            f"Found: {encoder_types!r}"
        )

    encoder_name = get_encoder_name(encoder)

    remove_elements: list[EncoderProtocol] = []
    for value in encoder_types:
        if get_encoder_name(value) == encoder_name:
            remove_elements.append(value)
            break
    for element in remove_elements:
        encoder_types.remove(element)
    encoder_types.appendleft(cast(Encoder[Any], encoder))


def json_encode_default(
    value: Any,
) -> Any:
    """
    Encode a value to a JSON-compatible format using a list of encoder types.

    Parameters:
    value (Any): The value to encode.

    Returns:
    Any: The JSON-compatible encoded value.

    Raises:
    ValueError: If the value is not serializable by any provided encoder type.
    """
    encoder_types = ENCODER_TYPES.get()

    for encoder in encoder_types:
        if encoder.is_type(value):
            return encoder.serialize(value)

    # If no encoder was found, raise a ValueError
    raise ValueError(f"Object of type '{type(value).__name__}' is not JSON serializable.")


def json_encode(
    value: Any,
    *,
    json_encode_fn: Callable[..., Any] = json.dumps,
    post_transform_fn: Callable[[str], Any] | None = json.loads,
    with_encoders: Sequence[EncoderProtocol] | None = None,
) -> Any:
    """
    Encode a value to a JSON-compatible format using a list of encoder types.

    Parameters:
    value (Any): The value to encode.
    json_encode_fn (Callable): The callable used for encoding the object as json.
                                   Must support the default keyword argument.
                                   By default: json.dumps
    post_transform_fn (Callable): The callable used for post-transforming the json-string.
                                               Can be None to simply return a json string.
                                               By default: json.loads, for compatibility reasons,
                                               so a simplified structure is returned.
    with_encoders (Sequence[EncoderProtocol]): Overwrite the used encoders for this call only
                                               by providing an own Sequence of encoders.

    Returns:
    Any: The JSON-compatible encoded value.

    Raises:
    ValueError: If the value is not serializable by any provided encoder type.
    """
    if with_encoders is None:
        result = json_encode_fn(value, default=json_encode_default)
        if post_transform_fn is None:
            return result
        return post_transform_fn(result)
    else:
        token = ENCODER_TYPES.set(with_encoders)
        try:
            return json_encode(
                value, json_encode_fn=json_encode_fn, post_transform_fn=post_transform_fn
            )
        finally:
            ENCODER_TYPES.reset(token)


# alias for old internal only name
json_encoder = json_encode


def apply_structure(
    structure: Any,
    value: Any,
    *,
    with_encoders: Sequence[EncoderProtocol] | None = None,
) -> Any:
    """
    Apply structure to value. Decoding for e.g. input parameters

    Parameters:
    structure (Any): The structure to apply on the value.
    value (Any): The value to encode.

    Keyword-only
    with_encoders (Sequence[EncoderProtocol]): Overwrite the used encoders for this call only
                                               by providing an own Sequence of encoders.
                                               Note: only encoders with `encode` function and `is_structure_type`.

    Raises:
    ValueError: If the value is not serializable by any provided encoder type.
    """
    if with_encoders is None:
        encoder_types = ENCODER_TYPES.get()

        for encoder in encoder_types:
            if hasattr(encoder, "encode") and encoder.is_type(value):
                return encoder.serialize(value)
    else:
        token = ENCODER_TYPES.set(with_encoders)
        try:
            return apply_structure(structure=structure, value=value)
        finally:
            ENCODER_TYPES.reset(token)
