import pytest

from lilya.conf import settings
from lilya.testclient.utils import override_settings

pytestmark = pytest.mark.anyio


@override_settings(environment="test_func")
def test_can_override_settings():
    assert settings.environment == "test_func"


@override_settings(environment="test_func")
def test_name_of_settings():
    assert settings.__class__.__name__ == "TestSettings"


class TestInClass:
    @override_settings(environment="test_func")
    def test_can_override_settings(self):
        assert settings.environment == "test_func"

    @override_settings(environment="test_func")
    def test_name_of_settings(self):
        assert settings.__class__.__name__ == "TestSettings"


class TestInClassAsync:
    @override_settings(environment="test_func")
    async def test_can_override_settings(self, test_client_factory):
        assert settings.environment == "test_func"

    @override_settings(environment="test_func")
    async def test_name_of_settings(self, test_client_factory):
        assert settings.__class__.__name__ == "TestSettings"
