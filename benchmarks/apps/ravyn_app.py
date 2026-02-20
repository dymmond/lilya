from ravyn import Gateway, Ravyn, WebSocketGateway, get, post, websocket
from ravyn.core.datastructures import UploadFile
from ravyn.params import Body
from ravyn.requests import Request
from ravyn.responses import JSONResponse, PlainText, StreamingResponse
from ravyn.utils.enums import EncodingType
from ravyn.websockets import WebSocket


@get()
async def plaintext() -> PlainText:
    return PlainText("ok")


@get()
async def json_resp() -> JSONResponse:
    return JSONResponse({"ok": True, "n": 1})


@get()
async def params(request: Request) -> JSONResponse:
    _id = int(request.path_params["id"])
    return JSONResponse({"id": _id})


@get()
async def query(request: Request) -> JSONResponse:
    a = request.query_params.get("a")
    b = request.query_params.get("b")
    return JSONResponse({"a": a, "b": b})


@get()
async def headers(request: Request) -> JSONResponse:
    v = request.headers.get("x-bench", "")
    return JSONResponse({"x-bench": v})


@get()
async def cookies(request: Request) -> JSONResponse:
    got = request.cookies.get("bench", "")
    resp = JSONResponse({"bench": got})
    resp.set_cookie("bench", "1")
    return resp


@get()
async def stream() -> StreamingResponse:
    async def gen():
        for _ in range(32):
            yield b"x" * 1024

    return StreamingResponse(gen(), media_type="application/octet-stream")


@post()
async def upload(
    data: UploadFile = Body(media_type=EncodingType.MULTI_PART),
) -> JSONResponse:
    data = await data.read()
    size = len(data)
    return JSONResponse({"bytes": size})


@websocket("/")
async def ws_echo(socket: WebSocket) -> None:
    await socket.accept()
    msg = await socket.receive_bytes()
    await socket.send_bytes(msg)
    await socket.close()


app = Ravyn(
    routes=[
        Gateway("/plaintext", handler=plaintext),
        Gateway("/json", handler=json_resp),
        Gateway("/params/{id:int}", handler=params),
        Gateway("/query", handler=query),
        Gateway("/headers", handler=headers),
        Gateway("/cookies", handler=cookies),
        Gateway("/stream", handler=stream),
        Gateway("/upload", handler=upload),
        WebSocketGateway("/ws-echo", handler=ws_echo),
    ]
)
