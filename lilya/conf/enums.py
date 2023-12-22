from enum import Enum

from dymmond_settings.enums import EnvironmentType as EnvironmentType


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value  # type: ignore

    def __repr__(self) -> str:
        return str(self)
