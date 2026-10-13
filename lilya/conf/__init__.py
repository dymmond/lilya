from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, TypeVar

from monkay import Monkay

if TYPE_CHECKING:
    from lilya.apps import BaseLilya
    from lilya.conf.global_settings import Settings

ENVIRONMENT_VARIABLE = "LILYA_SETTINGS_MODULE"
_TSettings = TypeVar("_TSettings")

_monkay: Monkay[BaseLilya, Settings] = Monkay(
    globals(),
    settings_path=lambda: os.environ.get(
        ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings"
    ),
    with_instance=True,
)


if TYPE_CHECKING:

    class SettingsForward(Settings):
        def __getattr__(self, name: str) -> Any: ...
else:

    class SettingsForward:
        def __getattribute__(self, name: str) -> Any:
            return getattr(_monkay.settings, name)

        def __setattr__(self, name: str, value: Any) -> None:
            return setattr(_monkay.settings, name, value)


settings: SettingsForward = SettingsForward()


def get_settings(settings_type: type[_TSettings]) -> _TSettings:
    """Return the lazily loaded global settings with a consumer-defined type.

    The class argument is a static type witness and is checked against the
    configured settings instance at runtime.
    """
    configured_settings = _monkay.settings
    if not isinstance(configured_settings, settings_type):
        raise TypeError(f"Configured settings must be an instance of {settings_type.__qualname__}")
    return configured_settings


def __getattr__(name: str) -> Any:
    if name != "Settings":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from lilya.conf.global_settings import Settings

    globals()[name] = Settings
    return Settings


def reload_settings() -> None:
    """
    Reloads the global settings.
    """
    _monkay.settings = os.environ.get(ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings")
