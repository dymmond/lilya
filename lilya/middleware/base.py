from __future__ import annotations

import sys
from typing import Any, Callable, Iterator

from lilya.types import ASGIApp

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec


P = ParamSpec("P")


class DefineMiddleware:
    """
    Wrapper that create the middleware classes.
    """

    __slots__ = ("app", "args", "kwargs", "middleware")

    def __init__(self, cls: Callable[..., ASGIApp], *args: P.args, **kwargs: P.kwargs) -> None:
        self.middleware = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        return self.middleware(*args, **kwargs)

    def __iter__(self) -> Iterator[Any]:
        return iter((self.middleware, self.args, self.kwargs))

    def __repr__(self) -> str:
        args_repr = ", ".join(
            [self.middleware.__name__]
            + [f"{value!r}" for value in self.args]
            + [f"{key}={value!r}" for key, value in self.kwargs.items()]
        )
        return f"{self.__class__.__name__}({args_repr})"


Middleware = DefineMiddleware
