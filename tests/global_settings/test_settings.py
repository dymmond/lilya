from lilya.conf import settings
from lilya.conf.global_settings import Settings


def test_defaults():
    settings = Settings()

    assert settings.debug == False


def test_test_dict():
    settings = Settings()

    settings_dict = settings.dict()

    assert settings_dict["debug"] == False
    assert settings_dict["include_in_schema"] == True


def xtest_conf_settings():
    assert settings.debug == True
