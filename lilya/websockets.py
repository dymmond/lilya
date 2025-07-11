from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, cast

from lilya._internal._connection import Connection
from lilya.enums import Event, MessageMode, ScopeType, WebSocketState
from lilya.exceptions import WebSocketRuntimeError
from lilya.types import Message, Receive, Scope, Send


class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason or ""


class WebsocketMixin(Connection):
    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope)
        assert scope["type"] == ScopeType.WEBSOCKET
        self._receive = receive
        self._send = send
        self._accepted = False
        self.client_state = WebSocketState.CONNECTING
        self.application_state = WebSocketState.CONNECTING
        self._cleanup_callbacks: list[Callable[[], Any]] = []

    def raise_for_disconnect(self, message: Message) -> None:
        if message["type"] == Event.WEBSOCKET_DISCONNECT:
            raise WebSocketDisconnect(message["code"], message.get("reason"))

    async def raise_for_connection_state(self) -> None:
        if self.application_state != WebSocketState.CONNECTED:
            raise WebSocketRuntimeError('WebSocket is not connected. Need to call "accept" first.')


class WebSocket(WebsocketMixin):
    async def receive(self) -> Message:
        """
        Receive ASGI websocket messages, ensuring valid state transitions.
        """
        if self.client_state not in {WebSocketState.CONNECTING, WebSocketState.CONNECTED}:
            raise WebSocketRuntimeError(
                'Cannot call "receive" once a disconnect message has been received.'
            )

        message = await self._receive()
        message_type = message["type"]

        if self.client_state == WebSocketState.CONNECTING:
            if message_type != Event.WEBSOCKET_CONNECT:
                raise WebSocketRuntimeError(
                    f'Expected ASGI message "websocket.connect", but got {message_type!r}'
                )
            self.client_state = WebSocketState.CONNECTED
        elif self.client_state == WebSocketState.CONNECTED:
            if message_type not in {Event.WEBSOCKET_RECEIVE, Event.WEBSOCKET_DISCONNECT}:
                raise WebSocketRuntimeError(
                    "Expected ASGI message websocket.receive or "
                    f'"websocket.disconnect", but got {message_type!r}'
                )

            self.client_state = (
                WebSocketState.DISCONNECTED
                if message_type == Event.WEBSOCKET_DISCONNECT
                else self.client_state
            )
        return message

    def add_cleanup(self, fn: Callable[[], Any]) -> None:
        self._cleanup_callbacks.append(fn)

    async def send(self, message: Message) -> None:
        """
        Send ASGI websocket messages, ensuring valid state transitions.
        """
        if self.application_state not in {WebSocketState.CONNECTING, WebSocketState.CONNECTED}:
            raise WebSocketRuntimeError('Cannot call "send" once a close message has been sent.')

        message_type = message["type"]

        if self.application_state == WebSocketState.CONNECTING:
            if message_type not in {Event.WEBSOCKET_ACCEPT, Event.WEBSOCKET_CLOSE}:
                raise WebSocketRuntimeError(
                    'Expected ASGI message "websocket.accept" or '
                    f'"websocket.close", but got {message_type!r}'
                )
            self.application_state = (
                WebSocketState.DISCONNECTED
                if message_type == Event.WEBSOCKET_CLOSE
                else WebSocketState.CONNECTED
            )
        elif self.application_state == WebSocketState.CONNECTED:
            if message_type not in {Event.WEBSOCKET_SEND, Event.WEBSOCKET_CLOSE}:
                raise WebSocketRuntimeError(
                    'Expected ASGI message "websocket.send" or "websocket.close", '
                    f"but got {message_type!r}"
                )

            self.application_state = (
                WebSocketState.DISCONNECTED
                if message_type == Event.WEBSOCKET_CLOSE
                else self.application_state
            )
        await self._send(message)

    async def _connect(self) -> None:
        if self.client_state == WebSocketState.CONNECTING:
            message = await self._receive()
            assert message["type"] == Event.WEBSOCKET_CONNECT
        self.client_state = WebSocketState.CONNECTED

    async def accept(
        self,
        subprotocol: str | None = None,
        headers: Iterable[tuple[bytes, bytes]] | None = None,
    ) -> None:
        headers = headers or []

        await self._connect()
        message = {
            "type": "websocket.accept",
            "headers": headers,
            "subprotocol": subprotocol,
        }
        await self.send(message)

    async def receive_text(self) -> str:
        await self.raise_for_connection_state()

        message = await self.receive()
        self.raise_for_disconnect(message)
        return cast(str, message["text"])

    async def receive_bytes(self) -> bytes:
        await self.raise_for_connection_state()

        message = await self.receive()
        self.raise_for_disconnect(message)
        return cast(bytes, message["bytes"])

    async def receive_json(self, mode: str = "text") -> Any:
        if mode not in {MessageMode.TEXT, MessageMode.BINARY}:
            raise WebSocketRuntimeError('The "mode" argument should be "text" or "binary".')

        await self.raise_for_connection_state()

        message = await self.receive()
        self.raise_for_disconnect(message)

        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return json.loads(text)

    async def iter_text(self) -> AsyncIterator[str]:
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            ...  # pragma: no cover

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        try:
            while True:
                yield await self.receive_bytes()
        except WebSocketDisconnect:
            ...  # pragma: no cover

    async def iter_json(self) -> AsyncIterator[Any]:
        try:
            while True:
                yield await self.receive_json()
        except WebSocketDisconnect:
            ...  # pragma: no cover

    async def send_text(self, data: str) -> None:
        await self.send({"type": Event.WEBSOCKET_SEND, "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self.send({"type": Event.WEBSOCKET_SEND, "bytes": data})

    async def send_json(self, data: Any, mode: str = "text") -> None:
        if mode not in {MessageMode.TEXT, MessageMode.BINARY}:
            raise WebSocketRuntimeError('The "mode" argument should be "text" or "binary".')

        text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        (
            await self.send({"type": Event.WEBSOCKET_SEND, "text": text})
            if mode == MessageMode.TEXT
            else await self.send({"type": Event.WEBSOCKET_SEND, "bytes": text.encode("utf-8")})
        )

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        await self.send({"type": Event.WEBSOCKET_CLOSE, "code": code, "reason": reason or ""})

        for fn in self._cleanup_callbacks:
            maybe_await = fn()
            if inspect.isawaitable(maybe_await):
                await maybe_await


class WebSocketClose:
    def __init__(self, code: int = 1000, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason or ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": Event.WEBSOCKET_CLOSE, "code": self.code, "reason": self.reason})
