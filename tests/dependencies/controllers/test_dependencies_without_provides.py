import pytest
from msgspec import Struct
from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.controllers import Controller
from lilya.dependencies import Provide
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency_with_body_inferred():
    settings.infer_body = True

    class Test(Controller):
        async def get(self, request: Request, x: str):
            return {"x": x}

    app = Lilya(
        dependencies={"x": Provide(lambda: "app_value")}, routes=[Path("/test_app", handler=Test)]
    )

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}

    settings.infer_body = False


async def test_app_level_dependency():
    class Test(Controller):
        async def get(self, request: Request, x):
            return {"x": x}

    app = Lilya(
        dependencies={"x": Provide(lambda: "app_value")}, routes=[Path("/test_app", handler=Test)]
    )

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}


async def test_include_level_dependency():
    class Test(Controller):
        async def get(self, request: Request, y):
            return {"y": y}

    app = Lilya(
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path("/test_inc", handler=Test),
                ],
                dependencies={"y": Provide(lambda: "inc_value")},
            )
        ]
    )

    client = TestClient(app)

    res = client.get("/inc/test_inc")
    assert res.status_code == 200
    assert res.json() == {"y": "inc_value"}


async def test_controller_level_dependency():
    class Test(Controller):
        dependencies = {"y": Provide(lambda: "inc_value")}

        async def get(self, request: Request, y):
            return {"y": y}

    app = Lilya(
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path("/test_inc", handler=Test),
                ],
            )
        ]
    )

    client = TestClient(app)

    res = client.get("/inc/test_inc")
    assert res.status_code == 200
    assert res.json() == {"y": "inc_value"}


async def test_nested_include_dependencies():
    class Test(Controller):
        async def get(self, a, b):
            return {"a": a, "b": b}

    app = Lilya(
        routes=[
            Include(
                path="/parent",
                routes=[
                    Include(
                        path="/nested",
                        routes=[Path("/both", handler=Test)],
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
    class Test(Controller):
        async def get(self, k):
            return {"k": k}

    app = Lilya(
        dependencies={"k": Provide(lambda: "app")},
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path(
                        path="/override",
                        handler=Test,
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


async def test_nested_dependency_factories():
    class Test(Controller):
        async def get(self, first, second):
            return {"second": second}

    app = Lilya(
        dependencies={
            "first": Provide(lambda: "one"),
            "second": Provide(lambda first: f"{first}-two"),
        },
        routes=[Path("/nested", handler=Test)],
    )

    client = TestClient(app)
    res = client.get("/nested")
    assert res.status_code == 200
    assert res.json() == {"second": "one-two"}


async def test_caching_behavior():
    calls = {"count": 0}

    class Test(Controller):
        async def get(self, x):
            return {"x": x}

    async def factory():
        calls["count"] += 1
        return "cached"

    app = Lilya(
        dependencies={"x": Provide(factory, use_cache=True)}, routes=[Path("/cache", handler=Test)]
    )

    client = TestClient(app)

    r1 = client.get("/cache")
    r2 = client.get("/cache")

    assert calls["count"] == 1
    assert r1.json() == {"x": "cached"} and r2.json() == {"x": "cached"}


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
    class Test(Controller):
        async def get(self, model):
            return {"model": model.show()}

    app = Lilya(
        routes=[
            Path("/model", handler=Test),
        ],
        dependencies={"model": Provide(model)},
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

    class Test(Controller):
        async def get(self, foo):
            return {"a": foo.a, "b": foo.b}

    app = Lilya(
        dependencies={"foo": Provide(Foo, "hello", b=42)},
        routes=[
            Path("/foo", handler=Test),
        ],
    )

    client = TestClient(app)
    res = client.get("/foo")

    assert res.status_code == 200
    assert res.json() == {"a": "hello", "b": 42}


async def test_provide_with_only_keyword_args():
    class Bar:
        def __init__(self, x=1, y=2):
            self.x = x
            self.y = y

    class Test(Controller):
        async def get(self, bar):
            return {"x": bar.x, "y": bar.y}

    app = Lilya(
        dependencies={"bar": Provide(Bar, y=99)},
        routes=[
            Path("/bar", handler=Test),
        ],
    )

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

    class Test(Controller):
        async def get(self, m):
            return {"desc": m.describe()}

    app = Lilya(
        dependencies={"m": Provide(MyModel, id=7, name="xyz")},
        routes=[
            Path("/model", handler=Test),
        ],
    )

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

    class Test(Controller):
        async def get(self, msg):
            return {"sum": msg.summary()}

    app = Lilya(
        dependencies={"msg": Provide(Msg, "hi", 123)},
        routes=[
            Path("/msg", handler=Test),
        ],
    )

    client = TestClient(app)
    res = client.get("/msg")

    assert res.status_code == 200
    assert res.json() == {"sum": "hi-123"}


async def test_only_requested_dependency_is_injected():
    """
    Even though the app has two dependencies registered, the handler
    only asks for `second`, so `first` should be ignored
    entirely.
    """

    class Test(Controller):
        async def get(self, second):
            return {"second": second}

    def get_second():
        return "one-two"

    app = Lilya(
        dependencies={
            "first": Provide(lambda: "one"),
            "second": Provide(get_second),
        },
        routes=[Path("/only-second", handler=Test)],
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

    class Test(Controller):
        async def get(self, x):
            return {"x": x}

    app = Lilya(
        # no 'x' in here
        dependencies={"y": Provide(lambda: "y")},
        routes=[Path("/missing-x", handler=Test)],
    )
    client = TestClient(app)

    with pytest.raises(TypeError):
        client.get("/missing-x")
