from dataclasses import dataclass
from typing import Any


@dataclass
class Query:
    default: Any | None = None
    alias: str | None = None
    required: bool = False
    cast: type | None = None
    description: str | None = None
