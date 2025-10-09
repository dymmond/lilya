import pytest
from msgspec import Struct
from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.dependencies import Provides
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency_with_body_inferred():
    settings.infer_body = True
    app = Lilya(dependencies={"x": lambda: "app_value"})

    @app.get("/test_app")
    async def handler(request: Request, x: str):
        return {"x": x}

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}

    settings.infer_body = False


async def test_app_level_dependency():
    app = Lilya(dependencies={"x": lambda: "app_value"})

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
                dependencies={"y": lambda: "inc_value"},
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
                        dependencies={"b": lambda: "B_val"},
                    )
                ],
                dependencies={"a": lambda: "A_val"},
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
        dependencies={"k": lambda: "app"},
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path(
                        path="/override",
                        handler=handler,
                        dependencies={"k": lambda: "route"},
                    )
                ],
                dependencies={"k": lambda: "inc"},
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
            "first": lambda: "one",
            "second": lambda first: f"{first}-two",
        },
        routes=[Path("/nested", handler=handler)],
    )

    client = TestClient(app)
    res = client.get("/nested")
    assert res.status_code == 200
    assert res.json() == {"second": "one-two"}


class PydanticTestModel(BaseModel):
    def show(self):
        return "show"


class DummyModel:
    def __init__(self, **kwargs):
        self.name = None

    def show(self):
        return "show"


class StructDummy(Struct):
    def show(self):
        return "show"


@pytest.mark.parametrize(
    "model", [PydanticTestModel, DummyModel, StructDummy], ids=["pydantic", "python", "msgspec"]
)
async def test_with_models(test_client_factory, model):
    async def handler(model=Provides()):
        return {"model": model.show()}

    app = Lilya(
        routes=[
            Path("/model", handler=handler),
        ],
        dependencies={"model": model},
    )

    client = TestClient(app)

    res = client.get("/model")
    assert res.status_code == 200
    assert res.json() == {"model": "show"}


async def test_provide_with_positional_and_keyword_args():
    class Foo:
        def __init__(self, a, b=0):
            self.a = a
            self.b = b

    app = Lilya(dependencies={"foo": lambda: Foo("hello", b=42)})

    @app.get("/foo")
    async def handler(foo=Provides()):
        return {"a": foo.a, "b": foo.b}

    client = TestClient(app)
    res = client.get("/foo")

    assert res.status_code == 200
    assert res.json() == {"a": "hello", "b": 42}


async def test_provide_with_only_keyword_args():
    class Bar:
        def __init__(self, x=1, y=2):
            self.x = x
            self.y = y

    app = Lilya(dependencies={"bar": lambda: Bar(y=99)})

    @app.get("/bar")
    async def handler(bar=Provides()):
        return {"x": bar.x, "y": bar.y}

    client = TestClient(app)
    res = client.get("/bar")

    assert res.status_code == 200
    # x should be its default, y overridden
    assert res.json() == {"x": 1, "y": 99}


async def test_provide_with_pydantic_model_kwargs():
    class MyModel(BaseModel):
        id: int
        name: str

        def describe(self):
            return f"{self.id}:{self.name}"

    app = Lilya(dependencies={"m": lambda: MyModel(id=7, name="xyz")})

    @app.get("/model")
    async def handler(m=Provides()):
        return {"desc": m.describe()}

    client = TestClient(app)
    res = client.get("/model")

    assert res.status_code == 200
    assert res.json() == {"desc": "7:xyz"}


async def test_provide_with_msgspec_struct_args():
    from msgspec import Struct

    class Msg(Struct):
        foo: str
        bar: int

        def summary(self):
            return f"{self.foo}-{self.bar}"

    app = Lilya(dependencies={"msg": lambda: Msg("hi", 123)})

    @app.get("/msg")
    async def handler(msg=Provides()):
        return {"sum": msg.summary()}

    client = TestClient(app)
    res = client.get("/msg")

    assert res.status_code == 200
    assert res.json() == {"sum": "hi-123"}


async def test_only_requested_dependency_is_injected():
    """
    Even though the app has two dependencies registered, the handler
    only asks for `second=Provides()`, so `first` should be ignored
    entirely.
    """

    async def handler(second=Provides()):
        return {"second": second}

    def get_second():
        return "one-two"

    app = Lilya(
        dependencies={
            "first": lambda: "one",
            "second": lambda: get_second(),
        },
        routes=[Path("/only-second", handler=handler)],
    )
    client = TestClient(app)

    res = client.get("/only-second")
    assert res.status_code == 200
    assert res.json() == {"second": "one-two"}


async def test_missing_requested_dependency_raises_500():
    """
    If the handler asks for a dependency that hasn't been registered,
    we should get a 500/ImproperlyConfigured.
    """

    async def handler(x=Provides()):
        return {"x": x}

    app = Lilya(
        # no 'x' in here
        dependencies={"y": lambda: "y"},
        routes=[Path("/missing-x", handler=handler)],
    )
    client = TestClient(app)

    res = client.get("/missing-x")

    assert res.status_code == 500


async def test_websocket_app_level_dependency():
    """
    An app-level dependency should be injected into a WS handler.
    """
    app = Lilya(dependencies={"w": lambda: "ws_val"})

    @app.websocket("/ws")
    async def ws_route(websocket, w=Provides()):
        await websocket.accept()
        await websocket.send_json({"w": w})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
    assert data == {"w": "ws_val"}


async def test_websocket_include_level_dependency():
    """
    An Include-level dependency (on a child Lilya) should be injected.
    """
    # child app defines its own WS route and a local dep "y"
    child = Lilya(dependencies={"y": lambda: "inc_val"})

    @child.websocket("/echo")
    async def echo(ws, y=Provides()):
        await ws.accept()
        await ws.send_json({"y": y})
        await ws.close()

    # mount it under /inc
    app = Lilya(routes=[Include(path="/inc", app=child)])
    client = TestClient(app)

    with client.websocket_connect("/inc/echo") as ws:
        data = ws.receive_json()
    assert data == {"y": "inc_val"}


async def test_websocket_nested_include_dependencies():
    """
    If you nest two Includes with their own deps, both should apply.
    """
    # innermost, has b
    nested = Lilya(dependencies={"b": lambda: "B_val"})

    @nested.websocket("/both")
    async def both(ws, a=Provides(), b=Provides()):
        await ws.accept()
        await ws.send_json({"a": a, "b": b})
        await ws.close()

    # middle, has a and mounts nested at /nested
    parent = Lilya(
        dependencies={"a": lambda: "A_val"}, routes=[Include(path="/nested", app=nested)]
    )

    # top, just mounts parent at /parent
    app = Lilya(routes=[Include(path="/parent", app=parent)])
    client = TestClient(app)

    with client.websocket_connect("/parent/nested/both") as ws:
        data = ws.receive_json()
    assert data == {"a": "A_val", "b": "B_val"}
