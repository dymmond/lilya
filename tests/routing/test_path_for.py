from lilya.responses import Ok, Response
from lilya.websockets import WebSocket


def homepage():
    return Response("Hello, world", media_type="text/plain")


def users():
    return Response("All users", media_type="text/plain")


def user(request):
    content = "User " + request.path_params["username"]
    return Response(content, media_type="text/plain")


def user_me():
    content = "User fixed me"
    return Response(content, media_type="text/plain")


def disable_user(request):
    content = "User " + request.path_params["username"] + " disabled"
    return Response(content, media_type="text/plain")


def user_no_match():  # pragma: no cover
    content = "User fixed no match"
    return Response(content, media_type="text/plain")


async def partial_endpoint(arg):
    return Ok({"arg": arg})


async def partial_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"url": str(websocket.url)})
    await websocket.close()
