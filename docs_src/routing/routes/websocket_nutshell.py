from lilya.apps import Lilya
from lilya.routing import WebSocketPath
from lilya.websockets import WebSocket


async def world_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    msg = await websocket.receive_json()
    assert msg
    assert websocket
    await websocket.close()


app = Lilya(
    routes=[
        WebSocketPath(
            "/{path_param:str}",
            handler=world_socket,
        ),
    ]
)
