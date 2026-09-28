import asyncio
import inspect
import types

import pytest

from lilya.conf import settings
from lilya.testclient.utils import override_settings

pytestmark = pytest.mark.anyio


@override_settings(environment="test_func")
def test_can_override_settings():
    assert settings.environment == "test_func"


@override_settings(environment="test_func")
def test_name_of_settings():
    assert settings.__class__.__name__ == "AppTestSettings"


class TestInClass:
    @override_settings(environment="test_func")
    def test_can_override_settings(self):
        assert settings.environment == "test_func"

    @override_settings(environment="test_func")
    def test_name_of_settings(self):
        assert settings.__class__.__name__ == "AppTestSettings"


class TestInClassAsync:
    @override_settings(environment="test_func")
    async def test_can_override_settings(self, test_client_factory):
        assert settings.environment == "test_func"

    @override_settings(environment="test_func")
    async def test_name_of_settings(self, test_client_factory):
        assert settings.__class__.__name__ == "AppTestSettings"


@pytest.mark.parametrize("marked", [False, True])
async def test_generator_based_coroutine_uses_async_settings_wrapper(marked):
    observed = []

    @types.coroutine
    def legacy_test():
        if False:
            yield
        observed.append(settings.environment)

    if marked:
        legacy_test._is_coroutine = asyncio.coroutines._is_coroutine
    assert not inspect.iscoroutinefunction(legacy_test)
    assert asyncio.iscoroutinefunction(legacy_test) is marked

    wrapped = override_settings(environment="legacy_test")(legacy_test)
    assert inspect.iscoroutinefunction(wrapped)
    await wrapped()
    assert observed == ["legacy_test"]
