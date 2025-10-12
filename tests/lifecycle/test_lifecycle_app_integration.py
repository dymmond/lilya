import pytest

from lilya.apps import Lilya
from lilya.lifecycle import _clear_for_tests_only, on_shutdown, on_startup
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_lifecycle_hooks_run_in_lilya_app():
    called = []
    _clear_for_tests_only()

    @on_startup
    def global_startup():
        called.append("global_startup")

    @on_shutdown
    def global_shutdown():
        called.append("global_shutdown")

    async def local_startup():
        called.append("local_startup")

    async def local_shutdown():
        called.append("local_shutdown")

    async def home():
        return PlainText("ok")

    app = Lilya(
        routes=[Path("/", home)],
        on_startup=[local_startup],
        on_shutdown=[local_shutdown],
    )

    # When using TestClient, Lilya triggers startup/shutdown automatically
    with TestClient(app) as client:
        response = client.get("/")
        assert response.text == "ok"

    # Verify hook order
    assert called == [
        "global_startup",
        "local_startup",
        "local_shutdown",
        "global_shutdown",
    ]
