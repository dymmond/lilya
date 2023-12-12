from lilya.conf import settings
from lilya.conf.enums import EnvironmentType
from lilya.conf.global_settings import Settings


def test_defaults():
    settings = Settings()

    assert settings.debug is False


def test_test_dict():
    settings = Settings()

    settings_dict = settings.dict()

    assert settings_dict["debug"] is False
    assert settings_dict["include_in_schema"] is True


def test_test_tuple():
    settings = Settings()

    settings_dict = settings.tuple()

    assert len(settings_dict) == 4


def test_conf_settings():
    assert settings.debug is True
    assert settings.environment == EnvironmentType.TESTING
