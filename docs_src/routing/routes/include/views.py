from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.websockets import WebSocket


async def update_product(request: Request, product_id: int):
    data = await request.json()
    return {"product_id": product_id, "product_name": data["name"]}


async def home():
    return JSONResponse({"detail": "Hello world"})


async def another(request: Request):
    return {"detail": "Another world!"}


async def world_socket(socket: WebSocket):
    await socket.accept()
    msg = await socket.receive_json()
    assert msg
    assert socket
    await socket.close()
