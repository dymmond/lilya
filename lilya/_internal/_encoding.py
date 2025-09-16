import datetime
from decimal import Decimal
from typing import Any

_PROTECTED_TYPES = (
    type(None),
    int,
    float,
    Decimal,
    datetime.datetime,
    datetime.date,
    datetime.time,
)


class ExtraUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj: Any, *args: Any) -> None:
        self.obj = obj
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{super().__str__()}. You passed in {self.obj!r} ({type(self.obj)})"


def is_protected_type(obj: Any) -> bool:
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_str(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_str(
    s: Any, encoding: str = "utf-8", strings_only: bool = False, errors: str = "strict"
) -> Any | str:
    """
    Similar to smart_str(), except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), str):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if isinstance(s, bytes):
            s = str(s, encoding, errors)
        else:
            s = str(s)
    except UnicodeDecodeError as e:
        raise ExtraUnicodeDecodeError(s, *e.args) from e
    return s
