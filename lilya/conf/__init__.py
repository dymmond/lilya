from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from lilya._internal._module_loading import import_string
from lilya.conf.functional import LazyObject, empty

if TYPE_CHECKING:
    from lilya.conf.global_settings import Settings

ENVIRONMENT_VARIABLE = "LILYA_SETTINGS_MODULE"


@lru_cache
def reload_settings() -> type[Settings]:
    """
    Reloads the global settings.
    """
    settings_module: str = os.environ.get(
        ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings"
    )
    settings: type[Settings] = import_string(settings_module)
    return settings


class LilyaLazySettings(LazyObject):
    """
    A lazy proxy for either global Lilya settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Lilya uses the settings module pointed to by LILYA_SETTINGS_MODULE.
    """

    def _setup(self, name: str | None = None) -> None:
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time settings are needed, if the user hasn't
        configured settings manually.
        """
        settings_module: str = os.environ.get(
            ENVIRONMENT_VARIABLE, "lilya.conf.global_settings.Settings"
        )

        settings: type[Settings] = import_string(settings_module)

        for setting, _ in settings().dict().items():
            assert setting.islower(), f"{setting} should be in lowercase."

        self._wrapped = settings()

    def configure(self, override_settings: type[Settings]) -> None:
        """
        Making sure the settings are overriden by the settings_module
        provided by a given application and therefore use it as the application
        global.
        """
        self._wrapped = override_settings

    def __repr__(self: LilyaLazySettings) -> str:
        # Hardcode the class name as otherwise it yields 'Settings'.
        if self._wrapped is empty:
            return "<LilyaLazySettings [Unevaluated]>"
        return f'<LilyaLazySettings "{self._wrapped.__class__.__name__}">'

    @property
    def configured(self) -> Any:
        """Return True if the settings have already been configured."""
        return self._wrapped is not empty


settings: type[Settings] = LilyaLazySettings()  # type: ignore
