from typing import Any, Callable

from lilya._internal._iterables import BaseWrapper
from lilya.types import ASGIApp


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

    def __init__(self, cls: Callable[..., ASGIApp], *args: Any, **kwargs: Any) -> None:
        self.middleware = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: ASGIApp) -> Any:
        return self.middleware(*self.args, app=app, **self.kwargs)
