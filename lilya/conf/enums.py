from enum import StrEnum


class BaseEnum(StrEnum):
    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return str(self)


class EnvironmentType(BaseEnum):
    """
    An Enum for environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
