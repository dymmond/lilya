from typing import Any, Callable, Iterator

from lilya.types import ASGIApp


class Middleware:
    """
    Builds a wrapper middleware for all the classes.
    """

    def __init__(self, cls_obj: type, **kwargs: Any) -> None:
        self.cls_obj = cls_obj
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        return iter((self.cls_obj, self.kwargs))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        option_strings = [f"{key}={value!r}" for key, value in self.kwargs.items()]
        args_repr = ", ".join([self.cls_obj.__name__] + option_strings)
        return f"{class_name}({args_repr})"


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
