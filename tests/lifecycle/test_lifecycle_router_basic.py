import pytest

from lilya.lifecycle import _clear_for_tests_only, on_shutdown, on_startup
from lilya.routing import Router

pytestmark = pytest.mark.anyio


async def test_router_merges_global_and_local_hooks_correctly():
    called = []
    _clear_for_tests_only()

    @on_startup
    async def global_startup():
        called.append("global_startup")

    @on_shutdown
    async def global_shutdown():
        called.append("global_shutdown")

    async def local_startup():
        called.append("local_startup")

    async def local_shutdown():
        called.append("local_shutdown")

    router = Router(on_startup=[local_startup], on_shutdown=[local_shutdown])

    # Execute startup and shutdown hooks manually
    for fn in router.on_startup:
        result = fn()
        if hasattr(result, "__await__"):
            await result

    for fn in router.on_shutdown:
        result = fn()
        if hasattr(result, "__await__"):
            await result

    assert called == [
        "global_startup",
        "local_startup",
        "local_shutdown",
        "global_shutdown",
    ]
