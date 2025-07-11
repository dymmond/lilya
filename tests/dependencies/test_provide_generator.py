import pytest

from lilya.dependencies import Provide
from lilya.requests import Request

pytestmark = pytest.mark.asyncio


@pytest.fixture
def scope():
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/",
        "headers": [],
    }


@pytest.fixture
def request_scope(scope):
    return Request(scope)


async def test_unwrap_generator_and_teardown(request_scope):
    teardown_called = {"flag": False}

    # A dummy dependency that yields a value then sets flag in its finally block
    def dep_gen():
        try:
            yield "the-session"
        finally:
            teardown_called["flag"] = True

    provide = Provide(dep_gen)

    # Resolve should unwrap the generator and return the yielded value
    result = await provide.resolve(request_scope, dependencies_map={})
    assert result == "the-session"

    # teardown not yet called
    assert teardown_called["flag"] is False

    # when the request_scope closes, the generator.finally should fire
    await request_scope.close()
    assert teardown_called["flag"] is True


async def test_non_generator_dependency(request_scope):
    # simple factory
    def dep_plain():
        return 12345

    provide = Provide(dep_plain)

    result = await provide.resolve(request_scope, dependencies_map={})
    assert result == 12345


async def test_async_generator_dependency(request_scope):
    teardown_called = {"flag": False}

    async def dep_async_gen():
        try:
            yield "async-session"
        finally:
            teardown_called["flag"] = True

    provide = Provide(dep_async_gen)

    # Even though it's async, Provide.resolve should pull out the value
    result = await provide.resolve(request_scope, dependencies_map={})
    assert result == "async-session"
    assert teardown_called["flag"] is False

    # And cleanup on close
    await request_scope.close()
    assert teardown_called["flag"] is True
