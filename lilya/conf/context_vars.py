from __future__ import annotations

from contextvars import ContextVar

OVERRIDE: ContextVar[bool] = ContextVar("override_settings", default=None)


def get_override_settings() -> bool | None:
    """
    Gets the current active tenant in the context.
    """
    return OVERRIDE.get()


def set_override_settings(value: bool | None) -> None:
    """
    Sets the global tenant for the context of the queries.
    When a global tenant is set the `get_context_schema` -> `SCHEMA` is ignored.
    """
    OVERRIDE.set(value)
