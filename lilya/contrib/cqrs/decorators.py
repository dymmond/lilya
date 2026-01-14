from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .bus import CommandBus, QueryBus

# These instances provide a convenient "batteries-included" entry point for simple
# applications. Advanced users (e.g., using dependency injection or multiple
# contexts) should instantiate their own buses and pass them to the decorators.
default_command_bus = CommandBus()
default_query_bus = QueryBus()


def command(
    message_type: type[Any],
    bus: CommandBus | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a function as a Command Handler.

    This connects a specific Command message class to the decorated function within
    the specified (or default) CommandBus.

    Usage:
        @command_handler(MyCommand)
        async def handle_my_command(cmd: MyCommand) -> None:
            ...

    Args:
        message_type (type[Any]): The class of the command payload this function handles.
        bus (CommandBus | None): The bus instance to register with. Defaults to the
            global `default_command_bus` if not provided.

    Returns:
        Callable: The original decorated function (unmodified).
    """

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        target_bus = bus or default_command_bus
        target_bus.register(message_type, fn)
        return fn

    return wrapper


def query(
    message_type: type[Any],
    bus: QueryBus | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a function as a Query Handler.

    This connects a specific Query message class to the decorated function within
    the specified (or default) QueryBus.

    Usage:
        @query_handler(GetUserInfo)
        async def get_user_info(query: GetUserInfo) -> UserProfile:
            ...

    Args:
        message_type (type[Any]): The class of the query payload this function handles.
        bus (QueryBus | None): The bus instance to register with. Defaults to the
            global `default_query_bus` if not provided.

    Returns:
        Callable: The original decorated function (unmodified).
    """

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        target_bus = bus or default_query_bus
        target_bus.register(message_type, fn)
        return fn

    return wrapper
