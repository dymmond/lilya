from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .exceptions import HandlerAlreadyRegistered, HandlerNotFound


class HandlerRegistry:
    """
    A centralized registry for mapping message types to their executable handlers.

    This class maintains an in-memory dictionary that links a specific message class
    (Command or Query) to the function or callable responsible for processing it.
    It enforces a strict one-to-one relationship between a message type and a handler.

    Attributes:
        _map (dict[type[Any], Callable[..., Any]]): The internal storage mapping
            message classes to handler callables.
    """

    def __init__(self) -> None:
        """
        Initialize an empty handler registry.
        """
        self._map: dict[type[Any], Callable[..., Any]] = {}

    def register(self, message_type: type[Any], handler: Callable[..., Any]) -> None:
        """
        Register a handler for a specific message type.

        Args:
            message_type (type[Any]): The class of the message (Command/Query).
            handler (Callable[..., Any]): The function to execute when this message is received.

        Raises:
            HandlerAlreadyRegistered: If a handler is already associated with this message type.
        """
        if message_type in self._map:
            raise HandlerAlreadyRegistered(f"Handler for {message_type!r} already registered")
        self._map[message_type] = handler

    def get(self, message_type: type[Any]) -> Callable[..., Any]:
        """
        Retrieve the handler associated with a message type.

        Args:
            message_type (type[Any]): The class of the message.

        Returns:
            Callable[..., Any]: The registered handler function.

        Raises:
            HandlerNotFound: If no handler has been registered for this message type.
        """
        try:
            return self._map[message_type]
        except KeyError as exc:
            raise HandlerNotFound(f"No handler for {message_type!r}") from exc

    def clear(self) -> None:
        """
        Remove all registered handlers.

        Useful for resetting state during testing or application teardown.
        """
        self._map.clear()

    def __contains__(self, message_type: type[Any]) -> bool:
        """
        Check if a handler exists for the given message type.

        Args:
            message_type (type[Any]): The message class to check.

        Returns:
            bool: True if a handler is registered, False otherwise.
        """
        return message_type in self._map
