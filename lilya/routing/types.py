from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from lilya.datastructures import ScopeHandler, SendReceiveSniffer
from lilya.types import Scope

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    from lilya.routing.base import BasePath

    P = ParamSpec("P")

T = TypeVar("T")


class PathHandler(ScopeHandler):
    """
    Represents a route handler that handles incoming requests.

    Args:
        child_scope (Scope): The child scope of the handler.
        scope (Scope): The scope of the handler.
        sniffer (SendReceiveSniffer): The Sniffer.

    Attributes:
        child_scope (Scope): The child scope of the handler.
        scope (Scope): The scope of the handler.
        receive (Receive): The receive function for handling incoming messages.
        send (Send): The send function for sending messages.
        sniffer (SendReceiveSniffer): The Sniffer.
    """

    def __init__(self, child_scope: Scope, scope: Scope, sniffer: SendReceiveSniffer) -> None:
        super().__init__(scope=scope, receive=sniffer.receive, send=sniffer.send)
        self.child_scope = child_scope
        self.sniffer = sniffer


class NoMatchFound(Exception):
    """
    Raised by `.url_path_for(name, **path_params)` and `.url_path_for(name, **path_params)`
    if no matching route exists.
    """

    def __init__(self, name: str, path_params: dict[str, Any]) -> None:
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


class PassPartialMatches(BaseException):
    """
    Signals that the route handling should continue and not stop with the current route
    and partial matches should be transfered
    """

    partial_matches: Sequence[tuple[Any, BasePath, PathHandler]] = ()

    def __init__(self, *, partial_matches: Sequence[tuple[Any, BasePath, PathHandler]]) -> None:
        self.partial_matches = partial_matches


def get_name(handler: Callable[..., Any]) -> str:
    """
    Returns the name of a given handler.
    """
    if hasattr(handler, "func"):
        handler = handler.func

    return (
        handler.__name__
        if inspect.isroutine(handler) or inspect.isclass(handler)
        else handler.__class__.__name__
    )
