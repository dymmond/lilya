from __future__ import annotations

from typing import Any

from lilya import status
from lilya._internal._path import parse_path
from lilya.datastructures import URLPath
from lilya.enums import Match, ScopeType
from lilya.exceptions import ContinueRouting
from lilya.requests import Request
from lilya.responses import PlainText
from lilya.types import Receive, Scope, Send
from lilya.websockets import WebSocketClose


class BasePath:
    """
    The base of all paths (routes) for any ASGI application
    with Lilya.
    """

    def handle_signature(self) -> None:
        raise NotImplementedError()  # pragma: no cover

    def search(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Searches for a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Returns a URL of a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    def url_path_for(self, name: str, /, **path_params: Any) -> URLPath:
        """
        Returns a URL of a matching route.
        """
        raise NotImplementedError()  # pragma: no cover

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Dispatches the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        match, child_scope = self.search(scope)

        if match == Match.NONE:
            await self.handle_not_found(scope, receive, send)
            return

        scope.update(child_scope)
        await self.handle_dispatch(scope, receive, send)

    async def handle_not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the case when no match is found.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        if scope["type"] == ScopeType.HTTP:
            response = PlainText("Not Found", status_code=status.HTTP_404_NOT_FOUND)
            await response(scope, receive, send)
        elif scope["type"] == ScopeType.WEBSOCKET:
            websocket_close = WebSocketClose()
            await websocket_close(scope, receive, send)

    @staticmethod
    async def handle_not_found_fallthrough(scope: Scope, receive: Receive, send: Send) -> None:
        raise ContinueRouting()

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles the dispatch of the request to the appropriate handler.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.

        Returns:
            None
        """
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.dispatch(scope=scope, receive=receive, send=send)

    async def handle_exception_handlers(
        self, scope: Scope, receive: Receive, send: Send, exc: Exception
    ) -> None:
        """
        Manages exception handlers for HTTP and WebSocket scopes.

        Args:
            scope (dict): The ASGI scope.
            receive (callable): The receive function.
            send (callable): The send function.
            exc (Exception): The exception to handle.
        """
        status_code = self._get_status_code(exc)

        if scope["type"] == ScopeType.HTTP:
            await self._handle_http_exception(scope, receive, send, exc, status_code)
        elif scope["type"] == ScopeType.WEBSOCKET:
            await self._handle_websocket_exception(send, exc, status_code)

    def _get_status_code(self, exc: Exception) -> int:
        """
        Get the status code from the exception.

        Args:
            exc (Exception): The exception.

        Returns:
            int: The status code.
        """
        return getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def _handle_http_exception(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        exc: Exception,
        status_code: int,
    ) -> None:
        """
        Handle HTTP exceptions.

        Args:
            scope (dict): The ASGI scope.
            receive (callable): The receive function.
            send (callable): The send function.
            exc (Exception): The exception to handle.
            status_code (int): The status code.
        """
        exception_handler = self.exception_handlers.get(  # type: ignore[attr-defined]
            status_code
        ) or self.exception_handlers.get(exc.__class__)  # type: ignore[attr-defined]

        if exception_handler is None:
            raise exc

        request = Request(scope=scope, receive=receive, send=send)
        response = exception_handler(request, exc)
        await response(scope=scope, receive=receive, send=send)

    async def _handle_websocket_exception(
        self, send: Send, exc: Exception, status_code: int
    ) -> None:
        """
        Handle WebSocket exceptions.

        Args:
            send (callable): The send function.
            exc (Exception): The exception to handle.
            status_code (int): The status code.
        """
        reason = repr(exc)
        await send({"type": "websocket.close", "code": status_code, "reason": reason})

    @property
    def stringify_parameters(self) -> list[str]:  # pragma: no cover
        """
        Gets the param:type in string like list.
        Used for the directive `lilya show-urls`.
        """
        path_components = parse_path(self.path)  # type: ignore[attr-defined]
        parameters = [component for component in path_components if isinstance(component, tuple)]
        stringified_parameters = [f"{param.name}:{param.type}" for param in parameters]  # type: ignore[attr-defined]
        return stringified_parameters
