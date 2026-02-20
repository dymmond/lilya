from __future__ import annotations

from fastapi import FastAPI, File, Request, UploadFile, WebSocket
from fastapi.responses import PlainTextResponse, StreamingResponse

app = FastAPI()


@app.get("/plaintext")
async def plaintext():
    return PlainTextResponse("ok")


@app.get("/json")
async def json_resp():
    return {"ok": True, "n": 1}


@app.get("/params/{id}")
async def params(id: int):
    return {"id": id}


@app.get("/query")
async def query(a: str | None = None, b: str | None = None):
    return {"a": a, "b": b}


@app.get("/headers")
async def headers(request: Request):
    return {"x-bench": request.headers.get("x-bench", "")}


@app.get("/cookies")
async def cookies(request: Request):
    got = request.cookies.get("bench", "")
    # FastAPI return value can’t set cookie directly without Response object
    from fastapi import Response

    resp = Response(content=f'{{"bench":"{got}"}}', media_type="application/json")
    resp.set_cookie("bench", "1")
    return resp


@app.get("/stream")
async def stream():
    async def gen():
        for _ in range(32):
            yield b"x" * 1024

    return StreamingResponse(gen(), media_type="application/octet-stream")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    return {"bytes": len(data)}


@app.websocket("/ws-echo")
async def ws_echo(ws: WebSocket):
    await ws.accept()
    msg = await ws.receive_bytes()
    await ws.send_bytes(msg)
    await ws.close()
