import os
import sys
from typing import Any

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

from lilya.apps import ChildLilya
from lilya.conf import get_settings, reload_settings, settings
from lilya.conf.global_settings import Settings


class DisableOpenAPI(Settings):
    enable_openapi: bool = True


class ChildSettings(DisableOpenAPI):
    app_name: str = "child app"
    secret_key: str = "child key"


def test_get_settings_exposes_custom_settings_fields(monkeypatch):
    previous_settings_module = os.environ.get("LILYA_SETTINGS_MODULE")
    monkeypatch.setenv(
        "LILYA_SETTINGS_MODULE",
        f"{ChildSettings.__module__}.ChildSettings",
    )
    reload_settings()

    try:
        configured_settings = get_settings(ChildSettings)
        assert_type(configured_settings.app_name, str)
        assert configured_settings.app_name == "child app"
        assert_type(settings.app_name, Any)
        assert settings.app_name == "child app"
    finally:
        if previous_settings_module is None:
            monkeypatch.delenv("LILYA_SETTINGS_MODULE", raising=False)
        else:
            monkeypatch.setenv("LILYA_SETTINGS_MODULE", previous_settings_module)
        reload_settings()


def test_child_lilya_independent_settings(test_client_factory):
    child = ChildLilya(
        routes=[],
        settings_module="tests.app_settings.test_settings_module_string.ChildSettings",
    )

    assert child.settings.app_name == "child app"


class DebugSettings(ChildSettings):
    debug: bool = True


def test_overrride_settings_module(test_client_factory):
    child = ChildLilya(
        routes=[],
        settings_module="tests.app_settings.test_settings_module_string.DebugSettings",
    )

    assert child.settings.debug is True


def test_default_settings_module_in_boolean(test_client_factory):
    assert settings.debug is True


def test_get_settings_accepts_the_settings_type_as_a_type_witness():
    configured_settings = get_settings(Settings)

    assert isinstance(configured_settings, Settings)


def test_settings_is_available_from_the_conf_package():
    from lilya.conf import Settings as PublicSettings

    assert PublicSettings is Settings
