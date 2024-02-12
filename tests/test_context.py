from typing import Any, Dict

from lilya.context import Context
from lilya.routing import Path
from lilya.testclient import create_client


async def get_data(context: Context) -> Dict[str, Any]:
    data = {
        "method": context.handler.methods,
        "middlewares": context.handler.middleware,
    }
    return data


def test_context(test_client_factory):
    with create_client(routes=[Path(path="/", handler=get_data)]) as client:
        response = client.get("/")

        assert response.json() == {"method": ["GET", "HEAD"], "middlewares": None}


async def get_context_route(context: Context) -> Dict[str, Any]:
    data = {
        "method": context.handler.methods,
        "middlewares": context.handler.middleware,
    }
    return data


def test_context_route(test_client_factory):
    with create_client(
        routes=[Path(path="/", handler=get_context_route, methods=["GET", "PUT", "POST"])]
    ) as client:
        response = client.get("/")

        assert "method" in response.json()
        assert "middlewares" in response.json()


async def change_context(context: Context) -> Dict[str, Any]:
    ctx = context
    ctx.add_to_context("call", "ok")
    return ctx.get_context_data()


def test_add_to_context(test_client_factory):
    with create_client(routes=[Path(path="/", handler=change_context)]) as client:
        response = client.get("/")

        assert response.json()["call"] == "ok"
