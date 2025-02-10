from __future__ import annotations

from typing import Any, cast

from lilya.permissions.base import DefinePermission


def wrap_permission(
    permission: DefinePermission | Any,
) -> DefinePermission:
    """
    Wraps the given permission into a DefinePermission instance if it is not already one.
    Or else it will assume its a Lilya permission and wraps it.

    Args:
        permission (Union[DefinePermission, Any]): The permission to be wrapped.
    Returns:
        DefinePermission: The wrapped permission instance.
    """
    if isinstance(permission, DefinePermission):
        return permission
    return DefinePermission(cast(Any, permission))
