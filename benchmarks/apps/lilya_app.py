from __future__ import annotations

from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse, PlainText, Response, StreamingResponse
from lilya.routing import Path, WebSocketPath
from lilya.websockets import WebSocket


async def plaintext() -> Response:
    return PlainText("ok")


async def json_resp() -> Response:
    return JSONResponse({"ok": True, "n": 1})


async def params(request: Request) -> Response:
    _id = int(request.path_params["id"])
    return JSONResponse({"id": _id})


async def query(request: Request) -> Response:
    a = request.query_params.get("a")
    b = request.query_params.get("b")
    return JSONResponse({"a": a, "b": b})


async def headers(request: Request) -> Response:
    v = request.headers.get("x-bench", "")
    return JSONResponse({"x-bench": v})


async def cookies(request: Request) -> Response:
    got = request.cookies.get("bench", "")
    resp = JSONResponse({"bench": got})
    resp.set_cookie("bench", "1")
    return resp


async def stream() -> Response:
    async def gen():
        for _ in range(32):
            yield b"x" * 1024

    return StreamingResponse(gen(), media_type="application/octet-stream")


async def upload(request: Request) -> Response:
    form = await request.form()
    f = form.get("file")
    size = 0
    if f is not None:
        data = await f.read()
        size = len(data)
    return JSONResponse({"bytes": size})


async def ws_echo(ws: WebSocket) -> None:
    await ws.accept()
    msg = await ws.receive_bytes()
    await ws.send_bytes(msg)
    await ws.close()


app = Lilya(
    routes=[
        Path("/plaintext", handler=plaintext, methods=["GET"]),
        Path("/json", handler=json_resp, methods=["GET"]),
        Path("/params/{id:int}", handler=params, methods=["GET"]),
        Path("/query", handler=query, methods=["GET"]),
        Path("/headers", handler=headers, methods=["GET"]),
        Path("/cookies", handler=cookies, methods=["GET"]),
        Path("/stream", handler=stream, methods=["GET"]),
        Path("/upload", handler=upload, methods=["POST"]),
        WebSocketPath("/ws-echo", handler=ws_echo),
    ]
)
