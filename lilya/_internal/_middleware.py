from __future__ import annotations

from typing import Any, cast

from lilya.middleware.base import DefineMiddleware


def wrap_middleware(
    middleware: DefineMiddleware | Any,
) -> DefineMiddleware:
    """
    Wraps the given middleware into a DefineMiddleware instance if it is not already one.
    Or else it will assume its a Lilya permission and wraps it.

    Args:
        permission (Union["BasePermission", Any]): The permission to be wrapped.
    Returns:
        BasePermission: The wrapped permission instance.
    """
    if isinstance(middleware, DefineMiddleware):
        return middleware
    return DefineMiddleware(cast(Any, middleware))
