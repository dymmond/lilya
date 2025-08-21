from typing import Any

from pydantic import BaseModel

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.api_key import APIKeyInHeader
from lilya.dependencies import Provide, Provides, Security
from lilya.routing import Path
from lilya.testclient import create_client

api_key = APIKeyInHeader(name="key", description="An API Key Header")


class User(BaseModel):
    username: str


def get_current_user(oauth_header: str = Security(api_key)):
    if isinstance(oauth_header, BaseModel):
        return oauth_header
    user = User(username=oauth_header)
    return user


@openapi(security=[api_key])
def read_current_user(current_user: User = Provides()) -> Any:
    return current_user


def test_security_api_key():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            ),
        ],
    ) as client:
        response = client.get("/users/me", headers={"key": "secret"})
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "secret"}


def test_security_api_key_no_key():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            ),
        ],
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 403, response.text
        assert response.text == "Not authenticated"


def test_openapi_schema():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            ),
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
                "/users/me": {
                    "get": {
                        "security": [
                            {
                                "APIKeyInHeader": {
                                    "type": "apiKey",
                                    "description": "An API Key Header",
                                    "name": "key",
                                    "in": "header",
                                    "scheme_name": "APIKeyInHeader",
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
                    "APIKeyInHeader": {
                        "type": "apiKey",
                        "description": "An API Key Header",
                        "name": "key",
                        "in": "header",
                        "scheme_name": "APIKeyInHeader",
                    }
                },
            },
            "servers": [{"url": "/"}],
        }
