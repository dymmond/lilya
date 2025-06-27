from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, ParamSpec, cast

from lilya._internal._module_loading import import_string
from lilya.types import ASGIApp

P = ParamSpec("P")


class DefinePermission(Generic[P]):
    """
    Wrapper that creates a permission class.
    """

    __slots__ = ("app", "args", "kwargs", "permission_or_string")

    def __init__(
        self, cls: Callable[..., ASGIApp] | str, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        self.permission_or_string = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: ASGIApp, *args: P.args, **kwargs: P.kwargs) -> Any:
        return self.permission(app=app, *args, **kwargs)

    @property
    def permission(self) -> Callable[..., ASGIApp]:
        permission_or_string = self.permission_or_string
        if isinstance(permission_or_string, str):
            self.permission_or_string = permission_or_string = import_string(permission_or_string)
        return cast(Callable[..., ASGIApp], permission_or_string)

    def __iter__(self) -> Iterator[Any]:
        return iter((self.permission, self.args, self.kwargs))

    def __repr__(self) -> str:
        args_repr = ", ".join(
            [self.permission.__name__]
            + [f"{value!r}" for value in self.args]
            + [f"{key}={value!r}" for key, value in self.kwargs.items()]
        )
        return f"{self.__class__.__name__}({args_repr})"


Permission = DefinePermission
