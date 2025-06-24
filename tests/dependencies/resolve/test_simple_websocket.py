from typing import Any

import pytest

from lilya.apps import Lilya
from lilya.dependencies import Resolve
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def query_params(q: str | None = None, skip: int = 0, limit: int = 20) -> dict[str, Any]:
    return {"q": q, "skip": skip, "limit": limit}


async def get_params(websocket, params: dict[str, Any] = Resolve(query_params)) -> dict[str, Any]:
    return params


async def test_simple():
    """
    An app-level dependency should be injected into a WS handler.
    """
    app = Lilya()

    @app.websocket("/ws")
    async def ws_route(websocket, params: dict[str, Any] = Resolve(query_params)):
        await websocket.accept()
        await websocket.send_json(params)
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()

    assert data == {"q": None, "skip": 0, "limit": 20}
