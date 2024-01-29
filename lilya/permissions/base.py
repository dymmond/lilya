import sys
from typing import Any, Callable

from lilya._internal._iterables import BaseWrapper
from lilya.types import ASGIApp

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec


P = ParamSpec("P")


class Permission(BaseWrapper):
    """
    Builds a wrapper permission for all the classes.
    """

    ...


class CreatePermission:
    """
    Wrapper that creates a permission class.
    """

    __slots__ = ("app", "args", "kwargs", "permission")

    def __init__(self, cls: Callable[..., ASGIApp], *args: P.args, **kwargs: P.kwargs) -> None:
        self.permission = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: ASGIApp) -> Any:
        return Permission(self.permission, app=app, *self.args, **self.kwargs)  # noqa
