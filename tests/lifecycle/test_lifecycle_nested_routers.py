import pytest

from lilya.apps import ChildLilya, Lilya
from lilya.lifecycle import _clear_for_tests_only, on_shutdown, on_startup
from lilya.responses import PlainText
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_lifecycle_hooks_are_isolated_per_app():
    """
    Confirms that:
    - Global hooks always run.
    - Parent Lilya runs its own hooks.
    - Child Lilya hooks do NOT run automatically when included.
      Each app controls its own lifecycle.
    """
    called = []
    _clear_for_tests_only()

    @on_startup
    def global_startup():
        called.append("global_startup")

    @on_shutdown
    def global_shutdown():
        called.append("global_shutdown")

    async def child_startup():
        called.append("child_startup")

    async def child_shutdown():
        called.append("child_shutdown")

    async def main_startup():
        called.append("main_startup")

    async def main_shutdown():
        called.append("main_shutdown")

    async def handler():
        return PlainText("nested")

    # Define a child Lilya app with its own lifecycle
    child_app = ChildLilya(
        routes=[Path("/", handler)],
        on_startup=[child_startup],
        on_shutdown=[child_shutdown],
    )

    # Define the main app including the child
    app = Lilya(
        routes=[
            Include("/child", app=child_app),
        ],
        on_startup=[main_startup],
        on_shutdown=[main_shutdown],
    )

    # When using TestClient, only the main Lilya lifecycle runs.
    with TestClient(app) as client:
        response = client.get("/child/")
        assert response.text == "nested"

    assert called == [
        "global_startup",
        "main_startup",
        "main_shutdown",
        "global_shutdown",
    ]
