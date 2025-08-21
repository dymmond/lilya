from typing import Any

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.oauth2 import OAuth2PasswordBearer
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token", description="OAuth2PasswordBearer security scheme", auto_error=False
)


@openapi(security=[oauth2_scheme])
async def read_items(token: str | None = Provides()) -> dict[str, Any]:
    if token is None:
        return {"msg": "Create an account first"}
    return {"token": token}


def test_no_token():
    with create_client(
        routes=[
            Path("/items", handler=read_items, dependencies={"token": Provide(oauth2_scheme)})
        ],
    ) as client:
        response = client.get("/items")
        assert response.status_code == 200, response.text
        assert response.json() == {"msg": "Create an account first"}


def test_token():
    with create_client(
        routes=[
            Path("/items", handler=read_items, dependencies={"token": Provide(oauth2_scheme)})
        ],
    ) as client:
        response = client.get("/items", headers={"Authorization": "Bearer testtoken"})
        assert response.status_code == 200, response.text
        assert response.json() == {"token": "testtoken"}


def test_incorrect_token():
    with create_client(
        routes=[
            Path("/items", handler=read_items, dependencies={"token": Provide(oauth2_scheme)})
        ],
    ) as client:
        response = client.get("/items", headers={"Authorization": "Notexistent testtoken"})
        assert response.status_code == 200, response.text
        assert response.json() == {"msg": "Create an account first"}


def test_openapi_schema():
    with create_client(
        routes=[
            Path("/items", handler=read_items, dependencies={"token": Provide(oauth2_scheme)})
        ],
        enable_openapi=True,
    ) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200, response.text

        assert response.json() == {
            "openapi": "3.1.0",
            "info": {
                "title": "Lilya",
                "version": client.app.version,
                "summary": "Lilya application",
                "description": "Yet another framework/toolkit that delivers.",
                "contact": {
                    "name": "Lilya",
                    "url": "https://lilya.dev",
                    "email": "admin@myapp.com",
                },
            },
            "paths": {
                "/items": {
                    "get": {
                        "security": [
                            {
                                "OAuth2PasswordBearer": {
                                    "type": "oauth2",
                                    "description": "OAuth2PasswordBearer security scheme",
                                    "flows": {"password": {"tokenUrl": "/token", "scopes": {}}},
                                    "scheme_name": "OAuth2PasswordBearer",
                                }
                            }
                        ],
                        "parameters": [],
                        "responses": {"200": {"description": "Successful response"}},
                    }
                }
            },
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "OAuth2PasswordBearer": {
                        "type": "oauth2",
                        "description": "OAuth2PasswordBearer security scheme",
                        "flows": {"password": {"tokenUrl": "/token", "scopes": {}}},
                        "scheme_name": "OAuth2PasswordBearer",
                    }
                },
            },
            "servers": [{"url": "/"}],
        }
