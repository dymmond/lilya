from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, ParamSpec, cast
from warnings import warn

from lilya.compat import import_string
from lilya.types import ASGIApp

P = ParamSpec("P")


class DefineMiddleware(Generic[P]):
    """
    Wrapper that create the middleware classes.
    """

    __slots__ = ("app", "args", "kwargs", "middleware_or_string")

    def __init__(
        self, cls: Callable[..., ASGIApp] | str, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        self.middleware_or_string = cls
        self.args = args
        self.kwargs = kwargs

    @property
    def middleware(self) -> Callable[..., ASGIApp]:
        middleware_or_string = self.middleware_or_string
        if isinstance(middleware_or_string, str):
            self.middleware_or_string = middleware_or_string = import_string(middleware_or_string)
        return cast(Callable[..., ASGIApp], middleware_or_string)

    def __call__(self, app: ASGIApp) -> ASGIApp:
        return self.middleware(app, *self.args, **self.kwargs)

    def __iter__(self) -> Iterator[Any]:
        warn(
            "Extracting DefineMiddleware like an Iterator is deprecated.",
            DeprecationWarning,
            stacklevel=1,
        )
        return iter((self.middleware, self.args, self.kwargs))

    def __repr__(self) -> str:
        args_repr = ", ".join(
            [self.middleware.__name__]
            + [f"{value!r}" for value in cast(tuple[Any, ...], self.args)]
            + [f"{key}={value!r}" for key, value in cast(dict[str, Any], self.kwargs).items()]
        )
        return f"{self.__class__.__name__}({args_repr})"


Middleware = DefineMiddleware
