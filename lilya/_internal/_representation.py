from collections.abc import Callable, Generator
from typing import Any


class BaseRepr:
    __slots__ = ()

    def __to_representation__(self) -> Any:
        keys = self.__slots__
        if not keys and hasattr(self, "__dict__"):
            keys = self.__dict__.keys()  # type: ignore
        attrs = ((s, getattr(self, s)) for s in keys)  # type: ignore
        return [(a, v) for a, v in attrs if v is not None]  # type: ignore

    def __pretty__(self, fmt: Callable[[Any], Any], **kwargs: Any) -> Generator[Any, None, None]:
        """Used by devtools (https://python-devtools.helpmanual.io/) to pretty print objects."""
        yield self.__to_name__() + "("
        yield 1
        for name, value in self.__to_representation__():
            if name is not None:
                yield name + "="
            yield fmt(value)
            yield ","
            yield 0
        yield -1
        yield ")"

    def __rich_repr__(self) -> Any:
        """Used by Rich (https://rich.readthedocs.io/en/stable/pretty.html) to pretty print objects."""
        for name, field_repr in self.__to_representation__():
            yield field_repr if name is None else name, field_repr

    def __to_name__(self) -> str:
        return self.__class__.__name__


class Str(BaseRepr):
    """
    Representation of the string.
    """

    def __string__(self, value: str) -> str:
        return value.join(
            repr(v) if a is None else f"{a}={v!r}" for a, v in self.__to_representation__()
        )


class Repr(Str):
    """
    Used for object representation.
    """

    def __str__(self) -> str:
        return self.__string__(" ")

    def __repr__(self) -> str:
        return f"{self.__to_name__()}({self.__string__(', ')})"
