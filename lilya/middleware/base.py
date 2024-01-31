import sys
from typing import Any, Callable, Iterator

from lilya._internal._iterables import BaseWrapper
from lilya.types import ASGIApp

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec


P = ParamSpec("P")


class Middleware(BaseWrapper):
    """
    Builds a wrapper middleware for all the classes.
    """

    ...


class CreateMiddleware:
    """
    Wrapper that create the middleware classes.
    """

    __slots__ = ("app", "args", "kwargs", "middleware")

    def __init__(self, cls: Callable[..., ASGIApp], *args: P.args, **kwargs: P.kwargs) -> None:
        self.middleware = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs) -> Any:
        return self.middleware(app=app, *args, **kwargs)

    def __iter__(self) -> Iterator[Any]:
        return iter((self.middleware, self.args, self.kwargs))
