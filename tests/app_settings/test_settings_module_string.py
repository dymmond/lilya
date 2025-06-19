from dataclasses import dataclass

from lilya.apps import ChildLilya
from lilya.conf import settings
from lilya.conf.global_settings import Settings


@dataclass
class DisableOpenAPI(Settings):
    enable_openapi: bool = True


@dataclass
class ChildSettings(DisableOpenAPI):
    app_name: str = "child app"
    secret_key: str = "child key"


def test_child_lilya_independent_settings(test_client_factory):
    child = ChildLilya(
        routes=[],
        settings_module="tests.app_settings.test_settings_module_string.ChildSettings",
    )

    assert child.settings.app_name == "child app"


@dataclass
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
