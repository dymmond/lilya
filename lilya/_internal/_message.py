from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Address:
    host: str
    port: int
