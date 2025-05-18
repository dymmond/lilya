from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from lilya.conf import _monkay, settings
from lilya.datastructures import URLPath
from lilya.exceptions import ImproperlyConfigured
from lilya.types import ASGIApp

if TYPE_CHECKING:  # pragma: no cover
    from lilya.routing import BasePath


def include(arg: Any, pattern: str | None = None) -> list[BasePath]:
    """Simple retrieve functionality to make it easier to include
    routes in the urls. Example, nested routes.
    """
    if not isinstance(arg, str):
        raise ImproperlyConfigured("The value should be a string with the format <module>.<file>")

    if pattern is None:
        pattern = settings.default_route_pattern

    router_conf_module = import_module(arg)
    patterns: list[BasePath] = getattr(router_conf_module, pattern, None)

    assert patterns is not None, (
        f"There is no pattern {pattern} found in {arg}. Are you sure you configured it correctly?"
    )

    assert isinstance(patterns, list), f"{patterns} should be a list and not {type(patterns)}."
    return patterns


def reverse(name: str, app: ASGIApp | None = None, path_params: Any | None = None) -> URLPath:
    """
    Reverses the URL based on a name and parameters provided
    and returns a URLPath.
    """
    if path_params is None:
        path_params = {}

    app_or_settings: ASGIApp = app or _monkay.instance
    return cast(URLPath, app_or_settings.path_for(name, **path_params))
