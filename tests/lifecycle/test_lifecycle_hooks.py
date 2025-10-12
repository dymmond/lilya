import pytest

from lilya.lifecycle import _clear_for_tests_only, on_shutdown, on_startup
from lilya.routing import Router

pytestmark = pytest.mark.anyio


async def test_global_hooks_are_injected_into_router():
    called = []

    # Clear registry before test (important for isolation)
    _clear_for_tests_only()

    # Register global hooks
    @on_startup
    async def global_startup():
        called.append("global_startup")

    @on_shutdown
    async def global_shutdown():
        called.append("global_shutdown")

    # Define app-level hooks
    async def app_startup():
        called.append("app_startup")

    async def app_shutdown():
        called.append("app_shutdown")

    # Create Router with local hooks
    router = Router(
        on_startup=[app_startup],
        on_shutdown=[app_shutdown],
    )

    # Run startup hooks
    for hook in router.on_startup:
        result = hook()
        if hasattr(result, "__await__"):
            await result

    # Run shutdown hooks
    for hook in router.on_shutdown:
        result = hook()
        if hasattr(result, "__await__"):
            await result

    # Verify order: global startup first, app startup next
    # and app shutdown first, global shutdown last
    assert called == [
        "global_startup",
        "app_startup",
        "app_shutdown",
        "global_shutdown",
    ]


async def test_only_global_hooks_run_correctly():
    called = []
    _clear_for_tests_only()

    @on_startup
    def global_startup():
        called.append("sync_startup")

    @on_shutdown
    async def global_shutdown():
        called.append("async_shutdown")

    router = Router()

    # Run both phases
    for hook in router.on_startup:
        result = hook()
        if hasattr(result, "__await__"):
            await result

    for hook in router.on_shutdown:
        result = hook()
        if hasattr(result, "__await__"):
            await result

    assert called == ["sync_startup", "async_shutdown"]
