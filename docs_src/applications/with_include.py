from lilya.app import Lilya
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Include, Path, WebSocketPath
from lilya.websockets import WebSocket


async def homepage():
    return Ok({"message": "Hello, world!"})


async def me():
    username = "John Doe"
    return Ok({"message": "Hello, %s!" % username})


def user(request: Request):
    username = request.path_params["username"]
    return Ok({"message": "Hello, %s!" % username})


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, websocket!")
    await websocket.close()


def startup():
    print("Up up we go!")


routes = [
    Include(
        "/",
        routes=[
            Path("/home", handler=homepage),
            Path("/me", handler=me),
            Path("/user/{username}", handler=user),
            WebSocketPath("/ws", handler=websocket_endpoint),
        ],
    )
]

app = Lilya(routes=routes, on_startup=[startup])
