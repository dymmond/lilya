from typing import Any

from lilya.controllers import WebSocketController
from lilya.websockets import WebSocket


class ASGIApp(WebSocketController):
    encoding = "bytes"

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: Any):
        await websocket.send_bytes(b"Message: " + data)

    async def on_disconnect(self, websocket: WebSocket, close_code: int): ...
