from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, cast

from monkay import Monkay

if TYPE_CHECKING:
    from lilya.apps import BaseLilya
    from lilya.conf.global_settings import Settings

ENVIRONMENT_VARIABLE = "LILYA_SETTINGS_MODULE"

_monkay: Monkay[BaseLilya, Settings] = Monkay(
    globals(),
    settings_path=lambda: os.environ.get(
        ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings"
    ),
    with_instance=True,
)


class SettingsForward:
    def __getattribute__(self, name: str) -> Any:
        return getattr(_monkay.settings, name)

    def __setattr__(self, name: str, value: Any) -> None:
        return setattr(_monkay.settings, name, value)


settings: Settings = cast("Settings", SettingsForward())


def reload_settings() -> None:
    """
    Reloads the global settings.
    """
    _monkay.settings = os.environ.get(ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings")
