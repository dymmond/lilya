import pytest

from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.routing import Include
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency_override_for_provides():
    """
    When dependency_overrides is defined at app level,
    it should replace the dependency used by Provides().
    """

    async def original():
        return "original_value"

    async def override():
        return "overridden_value"

    app = Lilya(
        dependencies={"x": Provide(original)},
    )
    app.override_dependency("x", override)  # alternative way to set override

    @app.get("/override_provides")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)
    res = client.get("/override_provides")

    assert res.status_code == 200
    assert res.json() == {"x": "overridden_value"}


async def test_dependency_override_takes_precedence_over_includes():
    """
    Even if an Include defines its own dependency, the app-level override wins.
    """

    async def original():
        return "include_value"

    async def override():
        return "app_override_value"

    include_app = Lilya(dependencies={"y": Provide(original)})

    @include_app.get("/inner")
    async def inner(y=Provides()):
        return {"y": y}

    app = Lilya(
        routes=[Include(path="/inc", app=include_app)],
    )

    app.override_dependency("y", override)

    client = TestClient(app)
    res = client.get("/inc/inner")

    assert res.status_code == 200
    assert res.json() == {"y": "app_override_value"}


async def test_nested_includes_with_override_applies_to_all_levels():
    """
    Overrides should cascade even in nested Include setups.
    """

    async def a_dep():
        return "A_val"

    async def b_dep():
        return "B_val"

    async def override_a():
        return "A_override"

    nested = Lilya(dependencies={"b": Provide(b_dep)})

    @nested.get("/both")
    async def both(a=Provides(), b=Provides()):
        return {"a": a, "b": b}

    parent = Lilya(
        dependencies={"a": Provide(a_dep)},
        routes=[Include(path="/nested", app=nested)],
    )

    app = Lilya(
        routes=[Include(path="/parent", app=parent)],
    )

    app.override_dependency("a", override_a)

    client = TestClient(app)
    res = client.get("/parent/nested/both")

    assert res.status_code == 200
    assert res.json() == {"a": "A_override", "b": "B_val"}


async def test_override_can_be_changed_runtime():
    """
    Overrides set via .override_dependency() at runtime should take effect immediately.
    """

    async def get_item():
        return "A"

    async def override_item():
        return "B"

    app = Lilya(dependencies={"x": Provide(get_item)})

    @app.get("/item")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)
    # baseline
    res1 = client.get("/item")

    assert res1.json() == {"x": "A"}

    # override dynamically
    app.override_dependency("x", override_item)
    res2 = client.get("/item")

    assert res2.json() == {"x": "B"}

    # reset clears it back
    app.reset_dependency_overrides()
    res3 = client.get("/item")
    assert res3.json() == {"x": "A"}


async def test_websocket_dependency_override_applies():
    """
    WebSocket dependencies should also respect app-level overrides.
    """

    async def get_ws():
        return "real"

    async def override_ws():
        return "fake"

    app = Lilya(
        dependencies={"w": Provide(get_ws)},
    )

    app.override_dependency("w", override_ws)

    @app.websocket("/ws_override")
    async def ws_route(websocket, w=Provides()):
        await websocket.accept()
        await websocket.send_json({"w": w})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/ws_override") as ws:
        data = ws.receive_json()
    assert data == {"w": "fake"}
