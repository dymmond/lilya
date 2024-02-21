from lilya.types import Receive, Scope, Send
from lilya.websockets import WebSocket


async def app(scope: Scope, receive: Receive, send: Send):
    websocket = WebSocket(scope=scope, receive=receive, send=send)
    await websocket.accept()
    await websocket.send_json({"message": "Hello, world!"}, mode="binary")
    await websocket.close()
