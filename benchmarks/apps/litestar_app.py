from __future__ import annotations

from typing import Annotated

from litestar import Litestar, WebSocket, get, post, websocket
from litestar.connection import Request
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response, Stream


@get("/plaintext")
async def plaintext() -> Response:
    return Response(content="ok", media_type="text/plain")


@get("/json")
async def json_resp() -> dict:
    return {"ok": True, "n": 1}


@get("/params/{id:int}")
async def params(id: int) -> dict:
    return {"id": id}


@get("/query")
async def query(a: str | None = None, b: str | None = None) -> dict:
    return {"a": a, "b": b}


@get("/headers")
async def headers(request: Request) -> dict:
    return {"x-bench": request.headers.get("x-bench", "")}


@get("/cookies")
async def cookies(request: Request) -> Response:
    got = request.cookies.get("bench", "")
    resp = Response(content={"bench": got})
    resp.set_cookie("bench", "1")
    return resp


@get("/stream")
async def stream() -> Stream:
    async def gen():
        for _ in range(32):
            yield b"x" * 1024

    return Stream(gen(), media_type="application/octet-stream")


@post("/upload")
async def upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict:
    content = await data.read()
    return {"bytes": len(content)}


@websocket("/ws-echo")
async def ws_echo(socket: WebSocket) -> None:
    await socket.accept()
    msg = await socket.receive_bytes()
    await socket.send_bytes(msg)
    await socket.close()


app = Litestar(
    route_handlers=[
        plaintext,
        json_resp,
        params,
        query,
        headers,
        cookies,
        stream,
        upload,
        ws_echo,
    ]
)
