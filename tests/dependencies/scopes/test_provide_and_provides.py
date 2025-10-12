import pytest
from msgspec import Struct
from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.dependencies import Provide, Provides
from lilya.enums import Scope
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency_with_body_inferred():
    settings.infer_body = True
    app = Lilya(dependencies={"x": Provide(lambda: "app_value", scope=Scope.APP)})

    @app.get("/test_app")
    async def handler(request: Request, x=Provides()):
        return {"x": x}

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}

    settings.infer_body = False


async def test_app_level_dependency():
    app = Lilya(dependencies={"x": Provide(lambda: "app_value", scope=Scope.APP)})

    @app.get("/test_app")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.json() == {"x": "app_value"}


async def test_include_level_dependency():
    async def handler(y=Provides()):
        return {"y": y}

    app = Lilya(
        routes=[
            Include(
                path="/inc",
                routes=[Path("/test_inc", handler=handler)],
                dependencies={"y": Provide(lambda: "inc_value", scope=Scope.REQUEST)},
            )
        ]
    )

    res = TestClient(app).get("/inc/test_inc")
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
                        dependencies={"b": Provide(lambda: "B_val", scope=Scope.REQUEST)},
                    )
                ],
                dependencies={"a": Provide(lambda: "A_val", scope=Scope.REQUEST)},
            )
        ]
    )

    res = TestClient(app).get("/parent/nested/both")
    assert res.json() == {"a": "A_val", "b": "B_val"}


async def test_route_overrides_include_and_app():
    async def handler(k=Provides()):
        return {"k": k}

    app = Lilya(
        dependencies={"k": Provide(lambda: "app", scope=Scope.APP)},
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path(
                        path="/override",
                        handler=handler,
                        dependencies={"k": Provide(lambda: "route", scope=Scope.REQUEST)},
                    )
                ],
                dependencies={"k": Provide(lambda: "inc", scope=Scope.REQUEST)},
            )
        ],
    )

    res = TestClient(app).get("/inc/override")
    assert res.json() == {"k": "route"}


async def test_missing_dependency_returns_500():
    async def handler(x=Provides()):
        return {"x": x}

    app = Lilya(routes=[Path("/missing", handler=handler)])
    res = TestClient(app).get("/missing")
    assert res.status_code == 500


async def test_nested_dependency_factories():
    async def handler(first=Provides(), second=Provides()):
        return {"second": second}

    app = Lilya(
        dependencies={
            "first": Provide(lambda: "one", scope=Scope.REQUEST),
            "second": Provide(lambda first: f"{first}-two", scope=Scope.REQUEST),
        },
        routes=[Path("/nested", handler=handler)],
    )

    res = TestClient(app).get("/nested")
    assert res.json() == {"second": "one-two"}


async def test_caching_behavior_across_requests():
    calls = {"count": 0}

    async def factory():
        calls["count"] += 1
        return f"val-{calls['count']}"

    app = Lilya(dependencies={"x": Provide(factory, use_cache=True, scope=Scope.APP)})

    @app.get("/cache")
    async def handler(x=Provides()):
        return {"x": x}

    client = TestClient(app)
    r1, r2 = client.get("/cache"), client.get("/cache")

    assert calls["count"] == 1
    assert r1.json() == r2.json()


class PydanticModel(BaseModel):
    def show(self):
        return "show"


class DummyModel:
    def show(self):
        return "show"


class StructModel(Struct):
    def show(self):
        return "show"


@pytest.mark.parametrize(
    "model", [PydanticModel, DummyModel, StructModel], ids=["pydantic", "python", "msgspec"]
)
async def test_dependency_injection_with_model_types(model):
    async def handler(model=Provides()):
        return {"model": model.show()}

    app = Lilya(
        dependencies={"model": Provide(model, scope=Scope.REQUEST)},
        routes=[Path("/model", handler=handler)],
    )

    res = TestClient(app).get("/model")
    assert res.json() == {"model": "show"}


async def test_provide_with_args_and_kwargs():
    class Foo:
        def __init__(self, a, b=0):
            self.a, self.b = a, b

    app = Lilya(dependencies={"foo": Provide(Foo, "hello", b=42)})

    @app.get("/foo")
    async def handler(foo=Provides()):
        return {"a": foo.a, "b": foo.b}

    res = TestClient(app).get("/foo")
    assert res.json() == {"a": "hello", "b": 42}


async def test_provide_with_only_kwargs():
    class Bar:
        def __init__(self, x=1, y=2):
            self.x, self.y = x, y

    app = Lilya(dependencies={"bar": Provide(Bar, y=99)})

    @app.get("/bar")
    async def handler(bar=Provides()):
        return {"x": bar.x, "y": bar.y}

    res = TestClient(app).get("/bar")
    assert res.json() == {"x": 1, "y": 99}


async def test_pydantic_struct_kwargs_construction():
    from msgspec import Struct

    class Msg(Struct):
        foo: str
        bar: int

        def summary(self):
            return f"{self.foo}-{self.bar}"

    app = Lilya(dependencies={"msg": Provide(Msg, "hi", 123)})

    @app.get("/msg")
    async def handler(msg=Provides()):
        return {"sum": msg.summary()}

    res = TestClient(app).get("/msg")
    assert res.json() == {"sum": "hi-123"}


async def test_websocket_app_level_dependency():
    app = Lilya(dependencies={"w": Provide(lambda: "ws_val", scope=Scope.REQUEST)})

    @app.websocket("/ws")
    async def ws_route(ws, w=Provides()):
        await ws.accept()
        await ws.send_json({"w": w})
        await ws.close()

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
    assert data == {"w": "ws_val"}


async def test_websocket_nested_include_dependencies():
    nested = Lilya(dependencies={"b": Provide(lambda: "B_val", scope=Scope.REQUEST)})

    @nested.websocket("/both")
    async def both(ws, a=Provides(), b=Provides()):
        await ws.accept()
        await ws.send_json({"a": a, "b": b})
        await ws.close()

    parent = Lilya(
        dependencies={"a": Provide(lambda: "A_val", scope=Scope.REQUEST)},
        routes=[Include(path="/nested", app=nested)],
    )

    app = Lilya(routes=[Include(path="/parent", app=parent)])
    client = TestClient(app)

    with client.websocket_connect("/parent/nested/both") as ws:
        data = ws.receive_json()
    assert data == {"a": "A_val", "b": "B_val"}
