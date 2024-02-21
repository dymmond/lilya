from lilya.apps import Lilya
from lilya.routing import Include, WebSocketPath
from lilya.websockets import WebSocket


async def websocket_endpoint_switch(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"URL": str(websocket.path_for("websocket_endpoint"))})
    await websocket.close()


async def websocket_params_chat(websocket: WebSocket, chat: str):
    await websocket.accept()
    await websocket.send_text(f"Hello, {chat}!")
    await websocket.close()


async def websocket_endpoint_include(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, new world!")
    await websocket.close()


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, world!")
    await websocket.close()


async def websocket_params(websocket: WebSocket, room: str):
    await websocket.accept()
    await websocket.send_text(f"Hello, {room}!")
    await websocket.close()


app = Lilya(
    routes=[
        WebSocketPath(
            path="/",
            handler=websocket_endpoint_switch,
            name="websocket_endpoint",
        ),
        WebSocketPath(
            "/ws",
            handler=websocket_endpoint,
            name="websocket_endpoint",
        ),
        WebSocketPath(
            "/ws/{room}",
            handler=websocket_params,
            name="ws-room",
        ),
        Include(
            "/websockets",
            routes=[
                WebSocketPath(
                    "/wsocket",
                    handler=websocket_endpoint_include,
                    name="wsocket",
                ),
                WebSocketPath(
                    "/wsocket/{chat}",
                    handler=websocket_params_chat,
                    name="ws-chat",
                ),
            ],
        ),
    ]
)
