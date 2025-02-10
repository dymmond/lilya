from __future__ import annotations

from typing import Any, cast

from lilya.middleware.base import DefineMiddleware


def wrap_middleware(
    middleware: DefineMiddleware | Any,
) -> DefineMiddleware:
    """
    Wraps the given middleware into a DefineMiddleware instance if it is not already one.
    Or else it will assume its a Lilya middleware and wraps it.

    Args:
        middleware (Union[DefineMiddleware, Any]): The middleware to be wrapped.
    Returns:
        DefineMiddleware: The wrapped middleware instance.
    """
    if isinstance(middleware, DefineMiddleware):
        return middleware
    return DefineMiddleware(cast(Any, middleware))
