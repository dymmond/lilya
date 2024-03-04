from __future__ import annotations

from typing import Any

from lilya.context import Context
from lilya.requests import Request
from lilya.routing import Path
from lilya.testclient import create_client


async def get_data(context: Context) -> dict[str, Any]:
    data = {
        "method": context.handler.methods,
        "middlewares": context.handler.middleware,
    }
    return data


def test_context(test_client_factory):
    with create_client(routes=[Path(path="/", handler=get_data)]) as client:
        response = client.get("/")

        assert response.json() == {"method": ["GET", "HEAD"], "middlewares": None}


async def get_context_route(context: Context) -> dict[str, Any]:
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


async def change_context(context: Context) -> dict[str, Any]:
    ctx = context
    ctx.add_to_context("call", "ok")
    return ctx.get_context_data()


def test_add_to_context(test_client_factory):
    with create_client(routes=[Path(path="/", handler=change_context)]) as client:
        response = client.get("/")

        assert response.json()["call"] == "ok"


async def context_with_request(
    context: Context,
    request: Request,
):
    data = {
        "is_request": isinstance(request, Request),
        "is_context": isinstance(context, Context),
    }
    return data


def test_context_and_request(test_client_factory):
    with create_client(routes=[Path(path="/", handler=context_with_request)]) as client:
        response = client.get("/")

        assert response.json()["is_request"] is True
        assert response.json()["is_context"] is True


async def request_with_context(
    request: Request,
    context: Context,
):
    data = {
        "is_request": isinstance(request, Request),
        "is_context": isinstance(context, Context),
    }
    return data


def test_request_and_context(test_client_factory):
    with create_client(routes=[Path(path="/", handler=request_with_context)]) as client:
        response = client.get("/")

        assert response.json()["is_request"] is True
        assert response.json()["is_context"] is True
