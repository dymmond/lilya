from lilya.apps import Lilya
from lilya.controllers import WebSocketController
from lilya.routing import Path
from lilya.websockets import WebSocket

class EchoController(WebSocketController):
    def __init__(self, scope, receive, send, *, prefix: str):
        super().__init__(scope, receive, send)
        self.prefix = prefix
        self.encoding = "text"

    async def on_receive(self, websocket: WebSocket, data: str) -> None:
        await websocket.send_text(f"{self.prefix}: {data}")

app = Lilya(
    routes=[Path("/ws", handler=EchoController.with_init(prefix="Echo"))]
)
