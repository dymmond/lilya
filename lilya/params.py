import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

TRUE_VALUES = {"true", "1", "yes", "on", "t"}
FALSE_VALUES = {"false", "0", "no", "off", "f"}


def _strip_annotated(cast: Any) -> Any:
    while get_origin(cast) is Annotated:
        cast = get_args(cast)[0]
    return cast


def _is_union(cast: Any) -> bool:
    return get_origin(cast) in (Union, UnionType)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set | frozenset):
        return list(value)
    return [value]


def _as_mapping(value: Any) -> Mapping[Any, Any]:
    if isinstance(value, Mapping):
        return value

    if isinstance(value, bytes):
        value = value.decode("utf-8")

    if isinstance(value, str):
        value = json.loads(value)
        if isinstance(value, Mapping):
            return value

    return dict(value)


def get_cast_name(cast: Any) -> str:
    return getattr(cast, "__name__", str(cast).replace("typing.", ""))


@dataclass
class BaseParam:
    def __cast__(self, value: Any, cast: Any) -> Any:
        cast = _strip_annotated(cast)

        if cast is Any or cast is object:
            return value

        if _is_union(cast):
            union_types = [typ for typ in get_args(cast) if typ is not type(None)]
            if value is None and len(union_types) != len(get_args(cast)):
                return None

            if isinstance(value, str) and str in union_types and len(union_types) > 1:
                union_types = [typ for typ in union_types if typ is not str] + [str]

            for typ in union_types:
                try:
                    return self.__cast__(value, typ)
                except (TypeError, ValueError):
                    continue
            raise ValueError(f"Cannot cast value {value!r} to {get_cast_name(cast)}")

        origin = get_origin(cast)
        args = get_args(cast)

        if cast is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in TRUE_VALUES:
                    return True
                if value_lower in FALSE_VALUES:
                    return False
                raise ValueError(f"Cannot cast value {value!r} to bool")
            return bool(value)

        if cast is list or origin is list:
            values = _as_list(value)
            item_cast = args[0] if args else Any
            return [self.__cast__(item, item_cast) for item in values]

        if cast is tuple or origin is tuple:
            values = _as_list(value)
            if not args:
                return tuple(values)
            if len(args) == 2 and args[1] is Ellipsis:
                return tuple(self.__cast__(item, args[0]) for item in values)
            return tuple(
                self.__cast__(item, item_cast)
                for item, item_cast in zip(values, args, strict=False)
            )

        if cast is set or origin is set:
            values = _as_list(value)
            item_cast = args[0] if args else Any
            return {self.__cast__(item, item_cast) for item in values}

        if cast is frozenset or origin is frozenset:
            values = _as_list(value)
            item_cast = args[0] if args else Any
            return frozenset(self.__cast__(item, item_cast) for item in values)

        if cast is dict or origin is dict:
            mapping = _as_mapping(value)
            key_cast, value_cast = args or (Any, Any)
            return {
                self.__cast__(key, key_cast): self.__cast__(item, value_cast)
                for key, item in mapping.items()
            }

        return cast(value)


@dataclass
class Query(BaseParam):
    default: Any | None = None
    alias: str | None = None
    required: bool = False
    cast: Any | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: Any) -> Any:
        return self.__cast__(value, cast) if cast else value


@dataclass
class Header(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: Any | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: Any) -> Any:
        return self.__cast__(value, cast) if cast else value


@dataclass
class Cookie(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: Any | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: Any) -> Any:
        return self.__cast__(value, cast) if cast else value
