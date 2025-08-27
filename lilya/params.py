from dataclasses import dataclass
from typing import Any


@dataclass
class BaseParam:
    def __post_init__(self) -> None:
        if self.cast:
            try:
                self.default = (
                    str(self.default).lower() in ("true", "1", "yes", "on", "t")
                    if self.cast
                    else self.cast(self.default)
                )
            except Exception:
                ...


@dataclass
class Query(BaseParam):
    default: Any | None = None
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None


@dataclass
class Header(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None


@dataclass
class Cookie(BaseParam):
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None
