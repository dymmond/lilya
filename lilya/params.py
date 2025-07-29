from dataclasses import dataclass
from typing import Any


@dataclass
class Query:
    default: Any | None = None
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None


@dataclass
class Header:
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None


@dataclass
class Cookie:
    value: Any
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None
