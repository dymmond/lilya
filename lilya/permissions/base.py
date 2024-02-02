import sys
from typing import Any, Callable, Iterator

from lilya.types import ASGIApp

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec


P = ParamSpec("P")


class DefinePermission:
    """
    Wrapper that creates a permission class.
    """

    __slots__ = ("app", "args", "kwargs", "permission")

    def __init__(self, cls: Callable[..., ASGIApp], *args: P.args, **kwargs: P.kwargs) -> None:
        self.permission = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs) -> Any:
        return self.permission(app=app, *args, **kwargs)

    def __iter__(self) -> Iterator[Any]:
        return iter((self.permission, self.args, self.kwargs))


Permission = DefinePermission
