from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Coroutine, Generator
from functools import cached_property
from typing import Any, cast

from lilya import status
from lilya._internal._responses import BaseHandler
from lilya.conf import settings
from lilya.enums import Event, HTTPMethod, ScopeType, SignatureDefault
from lilya.exceptions import HTTPException, ImproperlyConfigured
from lilya.requests import Request
from lilya.responses import PlainText, Response
from lilya.types import Message, Receive, Scope, Send
from lilya.websockets import WebSocket


class BaseController(BaseHandler):
    permissions: list[Callable[..., Coroutine[Any, Any, bool]]] = []
    middleware: list[Callable[..., Coroutine[Any, Any, None]]] = []
    exception_handlers: dict[int, Callable[[Request, Exception], Response]] = {}
    dependencies: dict[str, Any] = {}
    before_request: list[Callable[..., Coroutine[Any, Any, None]]] = []
    after_request: list[Callable[..., Coroutine[Any, Any, None]]] = []

    __is_controller__: bool = True

    def handle_signature(self) -> None:
        """
        Validates the return annotation of a handler
        if `enforce_return_annotation` is set to True.
        """
        if not settings.enforce_return_annotation:
            return None

        if self.signature.return_annotation is inspect._empty:
            raise ImproperlyConfigured(
                "A return value of a route handler function should be type annotated. "
                "If your function doesn't return a value or returns None, annotate it as returning 'NoReturn' or 'None' respectively."
            )


class Controller(BaseController):
    """
    Object oriented controller allowing the
    declaration of the http verbs as views.
    """

    __scope__: Scope | None = None

    signature: inspect.Signature | None = None

    @cached_property
    def __allowed_methods__(self) -> list[str]:
        return [
            method
            for method in HTTPMethod.to_list()
            if getattr(self, method.lower(), None) is not None
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == ScopeType.HTTP, (
            f"{self.__class__.__name__} classes must be in the http scope."
        )

        await self.handle_dispatch(scope=scope, receive=receive, send=send)

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope=scope, receive=receive, send=send)
        name = (
            HTTPMethod.GET.lower()
            if request.method == HTTPMethod.HEAD and not hasattr(self, "head")
            else request.method.lower()
        )
        handler: Callable[[], Coroutine[Any, Any, Response]] = getattr(
            self, name, self.handle_not_allowed
        )
        self.signature = inspect.signature(handler)
        self.__scope__ = scope

        func_params: dict[str, Any] = await self._extract_params_from_request(
            request=request, signature=self.signature
        )

        # Assign query params automatically.
        request_information = await self.extract_request_params_information(
            request=request, signature=self.signature
        )
        func_params.update(**request_information)

        if self.signature.parameters:
            if SignatureDefault.REQUEST in self.signature.parameters:
                func_params.update({"request": request})
                response = await self._execute_function(handler, **func_params)
            else:
                response = await self._execute_function(handler, **func_params)
        else:
            response = await self._execute_function(handler, **func_params)

        await self._handle_response_content(response, scope, receive, send)

    async def handle_not_allowed(self) -> Response:
        headers = {"Allow": ", ".join(self.__allowed_methods__)}
        if "app" in self.__scope__:
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
        return PlainText(
            "Method Not Allowed", status_code=status.HTTP_405_METHOD_NOT_ALLOWED, headers=headers
        )


class WebSocketController(BaseController):
    """
    Object oriented controller allowing the
    declaration of the http verbs as views.
    """

    encoding: str | None = None

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == ScopeType.WEBSOCKET, (
            f"{self.__class__.__name__} classes must be in the websocket scope."
        )
        self.scope = scope
        self.receive = receive
        self.send = send

    def __await__(self) -> Generator[Any, None, None]:
        return self.handle_dispatch(
            scope=self.scope, receive=self.receive, send=self.send
        ).__await__()

    async def handle_dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle WebSocket connection, message reception, and disconnection.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await self.on_connect(websocket)

        close_code = status.WS_1000_NORMAL_CLOSURE
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == Event.WEBSOCKET_RECEIVE:
                    data = await self.decode(websocket, message)
                    await self.on_receive(websocket, data)
                elif message["type"] == Event.WEBSOCKET_DISCONNECT:
                    close_code = int(message.get("code") or close_code)
                    break
        except Exception as e:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise e
        finally:
            await self.on_disconnect(websocket, close_code)

    async def decode(self, websocket: WebSocket, message: Message) -> Any:
        """
        Decode WebSocket messages based on the specified encoding.

        Args:
            websocket (WebSocket): WebSocket instance.
            message (Message): WebSocket message.

        Returns:
            Any: Decoded message data.
        """
        if self.encoding == "text":
            return await self.decode_text_message(websocket, message)
        elif self.encoding == "bytes":
            return await self.decode_bytes_message(websocket, message)
        elif self.encoding == "json":
            return await self.decode_json_message(message)

        assert self.encoding is None, f"Unsupported 'encoding' attribute {self.encoding}"
        return message["text"] if message.get("text") else message["bytes"]

    async def decode_text_message(self, websocket: WebSocket, message: Message) -> str:
        """
        Decode text WebSocket message.

        Args:
            websocket (WebSocket): WebSocket instance.
            message (Message): WebSocket message.

        Returns:
            str: Decoded text message.
        """
        if "text" not in message:
            await self.close_websocket(
                websocket, status.WS_1003_UNSUPPORTED_DATA, "Expected text messages, but got bytes"
            )
        return cast(str, message["text"])

    async def decode_bytes_message(self, websocket: WebSocket, message: Message) -> bytes:
        """
        Decode bytes WebSocket message.

        Args:
            websocket (WebSocket): WebSocket instance.
            message (Message): WebSocket message.

        Returns:
            bytes: Decoded bytes message.
        """
        if "bytes" not in message:
            await self.close_websocket(
                websocket, status.WS_1003_UNSUPPORTED_DATA, "Expected bytes messages, but got text"
            )
        return cast(bytes, message["bytes"])

    async def decode_json_message(self, message: Message) -> Any:
        """
        Decode JSON WebSocket message.

        Args:
            message (Message): WebSocket message.

        Returns:
            Any: Decoded JSON message data.
        """
        text = (
            message["text"]
            if message.get("text") is not None
            else message["bytes"].decode("utf-8")
        )
        try:
            return json.loads(text)
        except json.decoder.JSONDecodeError:
            raise RuntimeError("Malformed JSON data received.") from None

    async def on_connect(self, websocket: WebSocket) -> None:
        """
        Handle WebSocket connection.

        Args:
            websocket (WebSocket): WebSocket instance.
        """
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        """
        Handle WebSocket message reception.

        Args:
            websocket (WebSocket): WebSocket instance.
            data (Any): Decoded message data.
        """
        ...

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            websocket (WebSocket): WebSocket instance.
            close_code (int): WebSocket close code.
        """
        ...

    async def close_websocket(self, websocket: WebSocket, code: int, reason: str) -> None:
        """
        Close WebSocket connection with the specified code and reason.

        Args:
            websocket (WebSocket): WebSocket instance.
            code (int): WebSocket close code.
            reason (str): Reason for closing the WebSocket connection.
        """
        await websocket.close(code=code)
        raise RuntimeError(reason)
