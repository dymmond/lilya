from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

# A generic type variable for return values in QueryHandlers.
R = TypeVar("R")


class SupportsDict(Protocol):
    """
    Protocol for objects that can be serialized to a dictionary.

    This structural type is designed to support both Pydantic V2 (`model_dump`) `dict`
    interfaces transparently. It allows the messaging system to
    handle data models without being tightly coupled to a specific version of the
    validation library.
    """

    def model_dump(self) -> dict[str, Any]:
        """
        Convert the model to a dictionary (Pydantic V2 standard).
        """
        ...

    def dict(self) -> dict[str, Any]:
        """
        Convert the model to a dictionary.
        """
        ...


# A recursive type alias representing any data structure that is natively valid JSON.
# Useful for typing generic payloads or persistence fields.
JSONable = dict[str, Any] | list[Any] | str | int | float | bool | None


# -----------------------------------------------------------------------------
# Handler Types
# -----------------------------------------------------------------------------

# CommandHandler: A function that performs an action (side-effect) based on a message.
# It does not return a value (None). It may be synchronous or asynchronous.
CommandHandler = Callable[[Any], Awaitable[None] | None]

# QueryHandler: A function that retrieves data based on a message.
# It returns a result of type R. It may be synchronous or asynchronous.
QueryHandler = Callable[[Any], Awaitable[R] | R]


# -----------------------------------------------------------------------------
# Middleware Types
# -----------------------------------------------------------------------------

# Middleware: A component that intercepts message processing.
# It implements the "Chain of Responsibility" pattern, allowing logic (logging,
# metrics, auth) to run before or after the actual handler.
#
# Signature: (message, next_call) -> result
# - message: The input command or query object.
# - next_call: A function that invokes the next link in the chain (or the final handler).
Middleware = Callable[[Any, Callable[[Any], Awaitable[Any]]], Awaitable[Any]]
