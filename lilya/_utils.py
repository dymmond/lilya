from __future__ import annotations

import inspect
from collections.abc import Callable
from inspect import isclass
from typing import Any, TypeGuard, TypeVar, get_origin

T = TypeVar("T", bound=type)


def is_class_and_subclass(value: Any, _type: T | tuple[T, ...]) -> TypeGuard[T]:
    """
    Checks if a `value` is of type class and subclass.
    by checking the origin of the value against the type being
    verified.
    """
    original = get_origin(value)
    if not original and not isclass(value):
        return False

    try:
        if original:
            return original and issubclass(original, _type)
        return issubclass(value, _type)
    except TypeError:
        return False


def is_class_based_function(func: Callable[..., Any]) -> bool:
    """
    Checks if the function is a class-based function.
    This is determined by checking if the function is a class or a method.
    """
    if inspect.isclass(func) and callable(func):
        return True

    if callable(func) and not inspect.isfunction(func):
        return True
    return False


def is_method_defined_in_class(func: Callable[..., Any]) -> bool:
    """
    Checks if the function is a method defined in a class.
    This is determined by checking if the function's qualname contains a dot,
    which indicates that it is a method of a class.
    """
    if not inspect.isfunction(func):
        return False
    qualname = func.__qualname__
    return "." in qualname and "<locals>" not in qualname


def is_function(func: Callable[..., Any]) -> bool:
    """
    Checks if the function is a regular function.
    This is determined by checking if the function is callable and not a method defined in a class.
    """
    return inspect.isfunction(func) and not is_method_defined_in_class(func)
