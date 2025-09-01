import pytest
from msgspec import Struct
from pydantic import BaseModel

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.controllers import Controller
from lilya.dependencies import Provides
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_app_level_dependency_with_body_inferred():
    settings.infer_body = True

    class Test(Controller):
        async def get(self, request: Request, x: str):
            return {"x": x}

    app = Lilya(dependencies={"x": lambda: "app_value"}, routes=[Path("/test_app", handler=Test)])

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}

    settings.infer_body = False


async def test_app_level_dependency():
    class Test(Controller):
        async def get(self, request: Request, x=Provides()):
            return {"x": x}

    app = Lilya(dependencies={"x": lambda: "app_value"}, routes=[Path("/test_app", handler=Test)])

    client = TestClient(app)
    res = client.get("/test_app")
    assert res.status_code == 200
    assert res.json() == {"x": "app_value"}


async def test_include_level_dependency():
    class Test(Controller):
        async def get(self, request: Request, y=Provides()):
            return {"y": y}

    app = Lilya(
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path("/test_inc", handler=Test),
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
    class Test(Controller):
        async def get(self, a=Provides(), b=Provides()):
            return {"a": a, "b": b}

    app = Lilya(
        routes=[
            Include(
                path="/parent",
                routes=[
                    Include(
                        path="/nested",
                        routes=[Path("/both", handler=Test)],
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
    class Test(Controller):
        async def get(self, k=Provides()):
            return {"k": k}

    app = Lilya(
        dependencies={"k": lambda: "app"},
        routes=[
            Include(
                path="/inc",
                routes=[
                    Path(
                        path="/override",
                        handler=Test,
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
    class Test(Controller):
        async def get(self, x=Provides()):
            return {"x": x}

    app = Lilya(routes=[Path("/missing", handler=Test)])

    client = TestClient(app)
    res = client.get("/missing")
    assert res.status_code == 500


async def test_nested_dependency_factories():
    class Test(Controller):
        async def get(self, first=Provides(), second=Provides()):
            return {"second": second}

    app = Lilya(
        dependencies={
            "first": lambda: "one",
            "second": lambda first: f"{first}-two",
        },
        routes=[Path("/nested", handler=Test)],
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
    class Test(Controller):
        async def get(self, model=Provides()):
            return {"model": model.show()}

    app = Lilya(
        routes=[
            Path("/model", handler=Test),
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

    class Test(Controller):
        async def get(self, foo=Provides()):
            return {"a": foo.a, "b": foo.b}

    app = Lilya(
        dependencies={"foo": Foo("hello", b=42)},
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
        async def get(self, bar=Provides()):
            return {"x": bar.x, "y": bar.y}

    app = Lilya(
        dependencies={"bar": Bar(y=99)},
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

        def __hash__(self) -> int:
            return self.name.__hash__()  # or self.id.__hash__()

    class Test(Controller):
        async def get(self, m=Provides()):
            return {"desc": m.describe()}

    app = Lilya(
        dependencies={"m": MyModel(id=7, name="xyz")},
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

        def __hash__(self) -> int:
            return self.foo.__hash__()  # or self.id.__hash__()

    class Test(Controller):
        async def get(self, msg=Provides()):
            return {"sum": msg.summary()}

    app = Lilya(
        dependencies={"msg": Msg("hi", 123)},
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
    only asks for `second=Provides()`, so `first` should be ignored
    entirely.
    """

    class Test(Controller):
        async def get(self, second=Provides()):
            return {"second": second}

    def get_second():
        return "one-two"

    app = Lilya(
        dependencies={
            "first": lambda: "one",
            "second": lambda: get_second(),
        },
        routes=[Path("/only-second", handler=Test)],
    )
    client = TestClient(app)

    res = client.get("/only-second")
    assert res.status_code == 200
    assert res.json() == {"second": "one-two"}


async def test_missing_requested_dependency_raises_500():
    """
    If the handler asks for a dependency that hasn’t been registered,
    we should get a 500/ImproperlyConfigured.
    """

    class Test(Controller):
        async def get(self, x=Provides()):
            return {"x": x}

    app = Lilya(
        # no 'x' in here
        dependencies={"y": lambda: "y"},
        routes=[Path("/missing-x", handler=Test)],
    )
    client = TestClient(app)

    res = client.get("/missing-x")

    assert res.status_code == 500
