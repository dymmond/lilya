from __future__ import annotations

import json

from lilya.exceptions import ContinueRouting
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path, Router


def test_sniffing(test_client_factory):
    async def sniff1(request: Request):
        msg, body_initialized = await request.sniff()
        assert json.loads(msg["body"])
        assert body_initialized
        jsonob = await request.json()
        if "sniff1" not in jsonob:
            raise ContinueRouting()

        return JSONResponse({"sniff1": jsonob["sniff1"]}, media_type="text/plain")

    async def sniff2(request: Request):
        msg, body_initialized = await request.sniff()
        assert json.loads(msg["body"])
        assert body_initialized
        jsonob = await request.json()
        if "sniff2" not in jsonob:
            raise ContinueRouting()

        return JSONResponse({"sniff2": jsonob["sniff2"]}, media_type="text/plain")

    app = Router(
        [
            Path("/me", handler=sniff1, methods=["POST"]),
            Path("/me", handler=sniff2, methods=["POST"]),
        ]
    )
    with test_client_factory(app) as client:
        response = client.post("/me", json={"sniff1": "foobar123"})
        assert response.status_code == 200
        assert response.json() == {"sniff1": "foobar123"}

        response = client.post("/me", json={"sniff2": "edgylilya"})
        assert response.status_code == 200
        assert response.json() == {"sniff2": "edgylilya"}
        response = client.post("/me", json={"notexisting": "edgylilya"})
        assert response.status_code == 404


def test_sniffing_get(test_client_factory):
    async def sniff1(username: str, request: Request):
        if username == "me":
            raise ContinueRouting()
        return JSONResponse({"sniff1": "itsnotme"}, media_type="text/plain")

    async def sniff2(request: Request):
        return JSONResponse({"sniff2": "itsme"}, media_type="text/plain")

    app = Router(
        [
            Path("/user/{username}", handler=sniff1, methods=["GET"]),
            Path("/user/me", handler=sniff2, methods=["GET"]),
        ]
    )
    with test_client_factory(app) as client:
        response = client.get("/user/foo")
        assert response.status_code == 200
        assert response.json() == {"sniff1": "itsnotme"}

        response = client.get("/user/me")
        assert response.status_code == 200
        assert response.json() == {"sniff2": "itsme"}
