from __future__ import annotations

import contextlib
import io
import typing
from typing import TYPE_CHECKING
from urllib.parse import unquote

import anyio
import httpx
from anyio.abc import BlockingPortal

from lilya.testclient.exceptions import _Upgrade
from lilya.testclient.types import ASGI3App
from lilya.types import Message

if TYPE_CHECKING:
    from lilya.testclient.base import WebSocketTestSession


class TestClientTransport(httpx.BaseTransport):
    """
    Custom transport for HTTP and WebSocket requests in test client.

    Args:
        app (ASGI3App): The ASGI3 application handler.
        portal_factory (typing.Callable[[], contextlib.AbstractContextManager[anyio.abc.BlockingPortal]]):
            Factory function for creating a context manager for portal.
        raise_server_exceptions (bool, optional): Whether to raise server exceptions. Defaults to True.
        root_path (str, optional): The root path. Defaults to "".
        app_state (dict[str, typing.Any]): Application state.
    """

    def __init__(
        self,
        app: ASGI3App,
        portal_factory: typing.Callable[[], contextlib.AbstractContextManager[BlockingPortal]],
        raise_server_exceptions: bool = True,
        root_path: str = "",
        *,
        app_state: dict[str, typing.Any],
    ) -> None:
        self.app = app
        self.raise_server_exceptions = raise_server_exceptions
        self.root_path = root_path
        self.portal_factory = portal_factory
        self.app_state = app_state

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Handles an HTTP or WebSocket request.

        Args:
            request (httpx.Request): The HTTP request.

        Returns:
            httpx.Response: The HTTP response.
        """
        scheme = request.url.scheme
        netloc = request.url.netloc.decode(encoding="ascii")
        path = request.url.path
        raw_path = request.url.raw_path
        query = request.url.query.decode(encoding="ascii")

        default_port = {"http": 80, "ws": 80, "https": 443, "wss": 443}[scheme]

        host, port = self._parse_netloc(netloc, default_port)

        headers = self._build_headers(request.headers, host, port)

        if scheme in {"ws", "wss"}:
            return self._handle_websocket(path, raw_path, query, headers)

        return self._handle_http(path, raw_path, query, headers, request)

    def _parse_netloc(self, netloc: str, default_port: int) -> tuple[str, int]:
        """
        Parses the netloc to extract host and port.

        Args:
            netloc (str): The network location.
            default_port (int): The default port based on the scheme.

        Returns:
            tuple[str, int]: The host and port.
        """
        if ":" in netloc:
            host, port_string = netloc.split(":", 1)
            port = int(port_string)
        else:
            host = netloc
            port = default_port
        return host, port

    def _build_headers(
        self, request_headers: httpx.Headers, host: str, port: int
    ) -> list[tuple[bytes, bytes]]:
        """
        Builds headers for the request.

        Args:
            request_headers (httpx.Headers): The request headers.
            host (str): The host.
            port (int): The port.

        Returns:
            list[tuple[bytes, bytes]]: The built headers.
        """
        if "host" in request_headers:
            headers = []
        elif (
            port
            == {"http": 80, "ws": 80, "https": 443, "wss": 443}[request_headers["scheme"].decode()]
        ):
            headers = [(b"host", host.encode())]
        else:
            headers = [(b"host", f"{host}:{port}".encode())]

        headers += [
            (key.lower().encode(), value.encode()) for key, value in request_headers.multi_items()
        ]

        return headers

    def _handle_websocket(
        self,
        path: str,
        raw_path: bytes,
        query: str,
        headers: list[tuple[bytes, bytes]],
    ) -> httpx.Response:
        """
        Handles WebSocket requests.

        Args:
            path (str): The path.
            raw_path (bytes): The raw path.
            query (str): The query string.
            headers (list[tuple[bytes, bytes]]): The headers.

        Returns:
            httpx.Response: The HTTP response.
        """
        scope = {
            "type": "websocket",
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": "ws" if "ws" in headers else "wss",
            "query_string": query.encode(),
            "headers": headers,
            "client": None,
            "server": None,
            "subprotocols": [],
            "state": self.app_state.copy(),
            "extensions": {"websocket.http.response": {}},
        }
        session = self._create_websocket_session(scope)
        raise _Upgrade(session)

    def _create_websocket_session(self, scope: dict[str, typing.Any]) -> WebSocketTestSession:
        """
        Creates a WebSocket test session.

        Args:
            scope (dict[str, typing.Any]): The ASGI scope.

        Returns:
            WebSocketTestSession: The WebSocket test session.
        """
        return WebSocketTestSession(self.app, scope, self.portal_factory)

    def _handle_http(
        self,
        path: str,
        raw_path: bytes,
        query: str,
        headers: list[tuple[bytes, bytes]],
        request: httpx.Request,
    ) -> httpx.Response:
        """
        Handles HTTP requests.

        Args:
            path (str): The path.
            raw_path (bytes): The raw path.
            query (str): The query string.
            headers (list[tuple[bytes, bytes]]): The headers.
            request (httpx.Request): The HTTP request.

        Returns:
            httpx.Response: The HTTP response.
        """
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": request.url.scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": None,
            "server": None,
            "extensions": {"http.response.debug": {}},
            "state": self.app_state.copy(),
        }

        response = self._invoke_application(scope, request)
        return response

    def _invoke_application(
        self, scope: dict[str, typing.Any], request: typing.Any
    ) -> httpx.Response:
        """
        Invokes the ASGI application.

        Args:
            scope (dict[str, typing.Any]): The ASGI scope.

        Returns:
            httpx.Response: The HTTP response.
        """
        with self.portal_factory() as portal:
            response_complete = portal.call(anyio.Event)
            portal.call(self.app, scope, self._receive, self._send)

        if not response_complete.is_set():
            raw_kwargs = {
                "status_code": 500,
                "headers": [],
                "stream": io.BytesIO(),
            }
        else:
            raw_kwargs = self._finalize_response()

        raw_kwargs["stream"] = httpx.ByteStream(raw_kwargs["stream"].read())

        response = httpx.Response(**raw_kwargs, request=request)  # type: ignore
        return response

    async def _receive(self) -> Message:
        """
        Receives a message asynchronously.

        Returns:
            Message: The received message.
        """
        # Implementation based on your receive function; adjust as needed
        ...

    async def _send(self, message: Message) -> None:
        """
        Sends a message asynchronously.

        Args:
            message (Message): The message to send.
        """
        # Implementation based on your send function; adjust as needed
        ...

    def _finalize_response(self) -> dict[str, typing.Any]:
        """
        Finalizes the HTTP response.

        Returns:
            dict[str, typing.Any]: The response details.
        """
        # Implementation based on your response finalization; adjust as needed
        ...

    def _should_raise_exceptions(self, exc: BaseException) -> None:
        """
        Raises server exceptions if configured to do so.

        Args:
            exc (BaseException): The exception to raise.
        """
        if self.raise_server_exceptions:
            raise exc
