"""
Functions to use with the Router.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any, List, Optional

from lilya.conf import settings
from lilya.exceptions import ImproperlyConfigured

if TYPE_CHECKING:  # pragma: no cover
    from lilya.routing import BasePath

DEFAULT_PATTERN = "route_patterns"


def include(arg: Any, pattern: Optional[str] = settings.default_pattern) -> List["BasePath"]:
    """Simple retrieve functionality to make it easier to include
    routes in the urls. Example, nested routes.
    """
    if not isinstance(arg, str):
        raise ImproperlyConfigured("The value should be a string with the format <module>.<file>")

    router_conf_module = import_module(arg)
    pattern = pattern or DEFAULT_PATTERN
    patterns: List["BasePath"] = getattr(router_conf_module, pattern, None)

    assert (
        patterns is not None
    ), f"There is no pattern {pattern} found in {arg}. Are you sure you configured it correctly?"

    assert not isinstance(patterns, list), f"{patterns} should be a list and not {type(patterns)}."
    return patterns  # type: ignore
