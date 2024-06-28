from __future__ import annotations

from contextvars import ContextVar

OVERRIDE: ContextVar[bool] = ContextVar("override_settings", default=None)


def get_override_settings() -> bool | None:
    return OVERRIDE.get()


def set_override_settings(value: bool | None) -> None:
    OVERRIDE.set(value)
