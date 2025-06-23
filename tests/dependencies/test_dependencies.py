import pytest

from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency():
    app = Lilya(dependencies={"x": Provide(lambda: "app_value")})

    @app.get("/test_app")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}


async def test_include_level_dependency():
    async def handler(y=Provides()):
        return {"y": y}

    app = Lilya(
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path("/test_inc", handler=handler),
                ],
                dependencies={"y": Provide(lambda: "inc_value")},
            )
        ]
    )

    client = TestClient(app)

    res = client.get("/inc/test_inc")
    assert res.status_code == 200
    assert res.json() == {"y": "inc_value"}


async def test_nested_include_dependencies():
    async def both(a=Provides(), b=Provides()):
        return {"a": a, "b": b}

    app = Lilya(
        routes=[
            Include(
                path="/parent",
                routes=[
                    Include(
                        path="/nested",
                        routes=[Path("/both", handler=both)],
                        dependencies={"b": Provide(lambda: "B_val")},
                    )
                ],
                dependencies={"a": Provide(lambda: "A_val")},
            )
        ]
    )

    client = TestClient(app)

    res = client.get("/parent/nested/both")
    assert res.status_code == 200
    assert res.json() == {"a": "A_val", "b": "B_val"}


async def test_route_override_include_and_app():
    async def handler(k=Provides()):
        return {"k": k}

    app = Lilya(
        dependencies={"k": Provide(lambda: "app")},
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path(
                        path="/override",
                        handler=handler,
                        dependencies={"k": Provide(lambda: "route")},
                    )
                ],
                dependencies={"k": Provide(lambda: "inc")},
            )
        ],
    )

    client = TestClient(app)
    res = client.get("/inc/override")
    assert res.status_code == 200
    assert res.json() == {"k": "route"}


async def test_missing_dependency_returns_500():
    async def handler(x=Provides()):
        return {"x": x}

    app = Lilya(routes=[Path("/missing", handler=handler)])

    client = TestClient(app)
    res = client.get("/missing")
    assert res.status_code == 500


async def test_nested_dependency_factories():
    async def handler(first=Provides(), second=Provides()):
        return {"second": second}

    app = Lilya(
        dependencies={
            "first": Provide(lambda: "one"),
            "second": Provide(lambda first: f"{first}-two"),
        },
        routes=[Path("/nested", handler=handler)],
    )

    client = TestClient(app)
    res = client.get("/nested")
    assert res.status_code == 200
    assert res.json() == {"second": "one-two"}


async def test_caching_behavior():
    calls = {"count": 0}

    async def factory():
        calls["count"] += 1
        return "cached"

    app = Lilya(dependencies={"x": Provide(factory, use_cache=True)})

    @app.get("/cache")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)

    r1 = client.get("/cache")
    r2 = client.get("/cache")

    assert calls["count"] == 1
    assert r1.json() == {"x": "cached"} and r2.json() == {"x": "cached"}
