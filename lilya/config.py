from typing_extensions import TypedDict


class Config(TypedDict, total=False):
    """Configuration used by the settings system defining the behaviour."""

    allow_extra: bool
