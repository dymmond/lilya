from lilya.permissions import DefinePermission
from lilya.types import ASGIApp, Receive, Scope, Send


class CustomPermission:  # pragma: no cover
    def __init__(self, app: ASGIApp, foo: str, *, bar: int) -> None:
        self.app = app
        self.foo = foo
        self.bar = bar

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)


def test_permission_repr() -> None:
    middleware = DefinePermission(CustomPermission, "foo", bar=123)
    assert repr(middleware) == "DefinePermission(CustomPermission, 'foo', bar=123)"


def test_permission_iter() -> None:
    cls, args, kwargs = DefinePermission(CustomPermission, "foo", bar=123)
    assert (cls, args, kwargs) == (CustomPermission, ("foo",), {"bar": 123})
