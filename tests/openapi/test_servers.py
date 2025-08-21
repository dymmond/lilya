from typing import Any

from lilya.apps import Lilya
from lilya.contrib.openapi.config import OpenAPIConfig
from lilya.contrib.openapi.decorator import openapi
from lilya.routing import Path
from lilya.testclient import TestClient


class CustomOpenAPIConfig(OpenAPIConfig):
    servers: Any = [
        {"url": "/", "description": "Default server"},
        {
            "url": "http://staging.esmerald.dev",
            "description": "Staging of Esmerald",
        },
        {"url": "https://esmerald.dev"},
    ]


@openapi(summary="Bar", description="", operation_id="bar_bar_get")
async def bar() -> dict[str, str]:
    return {"hello": "world"}


app = Lilya(
    routes=[Path("/bar", handler=bar)],
    enable_openapi=True,
    openapi_config=CustomOpenAPIConfig(),
)


client = TestClient(app)


def test_application(test_client_factory):
    response = client.get("/bar")
    assert response.status_code == 200, response.json()


def test_openapi_schema(test_client_factory):
    response = client.get("/openapi.json")

    assert response.status_code == 200, response.text

    assert response.json() == {
        "openapi": "3.1.0",
        "info": {
            "title": "Lilya",
            "version": client.app.version,
            "summary": "Lilya application",
            "description": "Yet another framework/toolkit that delivers.",
            "contact": {"name": "Lilya", "url": "https://lilya.dev", "email": "admin@myapp.com"},
        },
        "paths": {
            "/bar": {
                "get": {
                    "operationId": "bar_bar_get",
                    "summary": "Bar",
                    "description": "",
                    "parameters": [],
                    "responses": {"200": {"description": "Successful response"}},
                }
            }
        },
        "components": {"schemas": {}, "securitySchemes": {}},
        "servers": [
            {"url": "/", "description": "Default server"},
            {"url": "http://staging.esmerald.dev", "description": "Staging of Esmerald"},
            {"url": "https://esmerald.dev"},
        ],
    }
