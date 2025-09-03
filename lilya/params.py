from dataclasses import dataclass
from typing import Any


@dataclass
class BaseParam:
    def __cast__(self, value: Any, cast: type) -> Any:
        try:
            if str(value).lower() in ("true", "1", "yes", "on", "t") and cast is bool:
                value = True
            elif str(value).lower() in ("false", "0", "no", "off", "f") and cast is bool:
                value = False
            else:
                value = cast(value)
        except Exception:
            raise
        return value


@dataclass
class Query(BaseParam):
    default: Any | None = None
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: type) -> Any:
        return self.__cast__(value, cast) if cast else value


@dataclass
class Header(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: type) -> Any:
        return self.__cast__(value, cast) if cast else value


@dataclass
class Cookie(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None

    def resolve(self, value: Any, cast: type) -> Any:
        return self.__cast__(value, cast) if cast else value
