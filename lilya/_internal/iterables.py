from typing import Any, Iterator


class BaseWrapper:
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
