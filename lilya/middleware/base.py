from typing import Any, Callable, ParamSpec

from lilya._internal._iterables import BaseWrapper
from lilya.types import ASGIApp

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

    def __call__(self, app: ASGIApp) -> Any:
        return Middleware(self.middleware, app=app, *self.args, **self.kwargs)  # noqa
