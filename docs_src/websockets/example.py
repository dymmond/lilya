from lilya.types import Receive, Scope, Send
from lilya.websockets import WebSocket


async def app(scope: Scope, receive: Receive, send: Send):
    websocket = WebSocket(scope=scope, receive=receive, send=send)
    await websocket.accept()

    async for message in websocket.iter_json():
        data = {"message": f"Message text was: {message}"}
        await websocket.send_json(data, mode="binary")
    await websocket.close()
