from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (
    JSONResponse,
    PlainTextResponse,
    Response,
    StreamingResponse,
)
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket


async def plaintext(_: Request) -> Response:
    return PlainTextResponse("ok")


async def json_resp(_: Request) -> Response:
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


async def stream(_: Request) -> Response:
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


app = Starlette(
    routes=[
        Route("/plaintext", plaintext, methods=["GET"]),
        Route("/json", json_resp, methods=["GET"]),
        Route("/params/{id:int}", params, methods=["GET"]),
        Route("/query", query, methods=["GET"]),
        Route("/headers", headers, methods=["GET"]),
        Route("/cookies", cookies, methods=["GET"]),
        Route("/stream", stream, methods=["GET"]),
        Route("/upload", upload, methods=["POST"]),
        WebSocketRoute("/ws-echo", ws_echo),
    ]
)
