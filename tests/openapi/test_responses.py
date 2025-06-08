from pydantic import BaseModel

from lilya import __version__
from lilya.contrib.openapi.datastructures import OpenAPIResponse
from lilya.contrib.openapi.decorator import openapi
from lilya.routing import Path
from lilya.testclient import create_client


class ErrorResponse(BaseModel):
    detail: str
    message: str


class User(BaseModel):
    name: str
    age: int


@openapi(
    summary="A test",
    description="A test",
    responses={
        400: OpenAPIResponse(model=ErrorResponse, description="Bad Request"),
        201: OpenAPIResponse(model=User, description="Ok"),
    },
)
async def create(user: User):
    return user


def test_responses_decorator(test_client_factory):
    with create_client(
        routes=[
            Path("/create", handler=create, methods=["POST"]),
        ]
    ) as client:
        response = client.get("/openapi.json")

        assert response.status_code == 200

        assert response.json() == {
            "openapi": "3.1.0",
            "info": {
                "title": "Lilya",
                "version": __version__,
                "summary": "Lilya application",
                "description": "Yet another framework/toolkit that delivers.",
                "contact": {
                    "name": "Lilya",
                    "url": "https://lilya.dev",
                    "email": "admin@myapp.com",
                },
            },
            "paths": {
                "/create": {
                    "post": {
                        "operationId": None,
                        "summary": "A test",
                        "description": "A test",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "name": {"title": "Name", "type": "string"},
                                            "age": {"title": "Age", "type": "integer"},
                                        },
                                        "required": ["name", "age"],
                                        "title": "User",
                                        "type": "object",
                                    }
                                }
                            }
                        },
                        "responses": {
                            "400": {
                                "description": "Bad Request",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "201": {
                                "description": "Ok",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                },
                            },
                        },
                    }
                }
            },
            "components": {
                "schemas": {
                    "ErrorResponse": {
                        "properties": {
                            "detail": {"title": "Detail", "type": "string"},
                            "message": {"title": "Message", "type": "string"},
                        },
                        "required": ["detail", "message"],
                        "title": "ErrorResponse",
                        "type": "object",
                    },
                    "User": {
                        "properties": {
                            "name": {"title": "Name", "type": "string"},
                            "age": {"title": "Age", "type": "integer"},
                        },
                        "required": ["name", "age"],
                        "title": "User",
                        "type": "object",
                    },
                }
            },
            "servers": [{"url": "/"}],
        }


@openapi()
async def create_again(user: User):
    return user


def test_responses_decorator_simple(test_client_factory):
    with create_client(
        routes=[
            Path("/item", handler=create_again, methods=["POST"]),
        ]
    ) as client:
        response = client.get("/openapi.json")

        assert response.status_code == 200

        assert response.json() == {
            "openapi": "3.1.0",
            "info": {
                "title": "Lilya",
                "version": __version__,
                "summary": "Lilya application",
                "description": "Yet another framework/toolkit that delivers.",
                "contact": {
                    "name": "Lilya",
                    "url": "https://lilya.dev",
                    "email": "admin@myapp.com",
                },
            },
            "paths": {
                "/item": {
                    "post": {
                        "operationId": None,
                        "requestBody": {"content": {"application/json": {"schema": {}}}},
                        "responses": {"200": {"description": "Successful response"}},
                    }
                }
            },
            "components": {"schemas": {}},
            "servers": [{"url": "/"}],
        }
