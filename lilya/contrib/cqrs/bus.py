from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .exceptions import InvalidMessage
from .registry import HandlerRegistry
from .types import Middleware


async def _maybe_await(x: Any) -> Any:
    """
    Await the object if it is a coroutine or awaitable, otherwise return it directly.

    This helper allows handlers to be either synchronous (`def`) or asynchronous
    (`async def`) transparently to the caller.
    """
    if inspect.isawaitable(x):
        return await x
    return x


class Pipeline:
    """
    A composition engine that wraps a terminal handler with a stack of middleware.

    This implements the "Onion Architecture" or "Chain of Responsibility" pattern.
    Each middleware layer receives the message and a `next` callable. It can execute
    logic before passing control deeper into the chain, and execute logic after the
    inner layers return.



    Attributes:
        _middleware (list[Middleware]): The ordered list of middleware functions.
    """

    def __init__(self, middleware: list[Middleware]) -> None:
        """
        Initialize the pipeline.

        Args:
            middleware (list[Middleware]): A list of middleware callables.
                Order matters: the first element is the outermost layer (runs first).
        """
        self._middleware = middleware

    def wrap(self, terminal: Callable[[Any], Awaitable[Any]]) -> Callable[[Any], Awaitable[Any]]:
        """
        Wrap the terminal handler with the configured middleware stack.

        Args:
            terminal (Callable[[Any], Awaitable[Any]]): The final function to call
                after all middleware have passed the message through.

        Returns:
            Callable[[Any], Awaitable[Any]]: A generic async callable that represents
                the entire pipeline.
        """

        async def call(msg: Any) -> Any:
            # Recursive function to traverse the middleware stack
            async def run_chain(index: int, current_msg: Any) -> Any:
                # Base case: we reached the end of the middleware list
                if index == len(self._middleware):
                    return await terminal(current_msg)

                # Recursive step: Call current middleware, passing the 'next' function
                # which resumes the chain at index + 1
                return await self._middleware[index](
                    current_msg, lambda n: run_chain(index + 1, n)
                )

            return await run_chain(0, msg)

        return call


class CommandBus:
    """
    The Command Bus acts as the dispatcher for write-side operations (Commands).

    It routes command objects to their registered handlers through a defined
    middleware pipeline. By convention, commands do not return values (they produce
    side effects or void).

    Attributes:
        _registry (HandlerRegistry): The internal map of Command types to Handlers.
        _pipeline (Pipeline): The middleware execution engine.
    """

    def __init__(
        self,
        registry: HandlerRegistry | None = None,
        middleware: list[Middleware] | None = None,
    ) -> None:
        """
        Initialize the CommandBus.

        Args:
            registry (HandlerRegistry | None): A pre-filled registry. If None,
                creates a new empty one.
            middleware (list[Middleware] | None): A list of middleware to apply
                to all commands dispatched through this bus.
        """
        self._registry = registry or HandlerRegistry()
        self._pipeline = Pipeline(middleware or [])

    def register(self, message_type: type[Any], handler: Callable[[Any], Any]) -> None:
        """
        Register a handler for a specific Command type.

        Args:
            message_type (type[Any]): The class of the command.
            handler (Callable[[Any], Any]): The function to execute.
        """
        self._registry.register(message_type, handler)

    async def dispatch(self, command: Any) -> None:
        """
        Send a command to its handler.

        This runs the command through the middleware pipeline and ensures the
        handler's result (if any) is awaited.

        Args:
            command (Any): The command object payload.

        Raises:
            InvalidMessage: If the command is None.
            HandlerNotFound: If no handler is registered for this command type.
        """
        if command is None:
            raise InvalidMessage("command cannot be None")

        # Resolve the specific handler for this command type
        handler = self._registry.get(type(command))

        # internal terminal function to standardize sync/async handlers
        async def terminal(msg: Any) -> Any:
            return await _maybe_await(handler(msg))

        # Wrap handler in middleware and execute
        wrapped = self._pipeline.wrap(terminal)
        await wrapped(command)


class QueryBus:
    """
    The Query Bus acts as the dispatcher for read-side operations (Queries).

    It routes query objects to their registered handlers and returns the result.
    Unlike commands, queries MUST return data and should generally not cause
    observable side effects.

    Attributes:
        _registry (HandlerRegistry): The internal map of Query types to Handlers.
        _pipeline (Pipeline): The middleware execution engine.
    """

    def __init__(
        self,
        registry: HandlerRegistry | None = None,
        middleware: list[Middleware] | None = None,
    ) -> None:
        """
        Initialize the QueryBus.

        Args:
            registry (HandlerRegistry | None): A pre-filled registry.
            middleware (list[Middleware] | None): A list of middleware to apply.
        """
        self._registry = registry or HandlerRegistry()
        self._pipeline = Pipeline(middleware or [])

    def register(self, message_type: type[Any], handler: Callable[[Any], Any]) -> None:
        """
        Register a handler for a specific Query type.

        Args:
            message_type (type[Any]): The class of the query.
            handler (Callable[[Any], Any]): The function that returns the result.
        """
        self._registry.register(message_type, handler)

    async def ask(self, query: Any) -> Any:
        """
        Send a query to its handler and retrieve the answer.

        Args:
            query (Any): The query object payload.

        Returns:
            Any: The result returned by the query handler.

        Raises:
            InvalidMessage: If the query is None.
            HandlerNotFound: If no handler is registered for this query type.
        """
        if query is None:
            raise InvalidMessage("query cannot be None")

        handler = self._registry.get(type(query))

        async def terminal(msg: Any) -> Any:
            return await _maybe_await(handler(msg))

        wrapped = self._pipeline.wrap(terminal)
        return await wrapped(query)
