from typing import Any

from pydantic import BaseModel

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.open_id import OpenIdConnect
from lilya.dependencies import Provide, Provides, Security
from lilya.routing import Path
from lilya.testclient import create_client

oid = OpenIdConnect(openIdConnectUrl="/openid", auto_error=False)


class User(BaseModel):
    username: str


def get_current_user(oauth_header: str | None = Security(oid)):
    if oauth_header is None:
        return None
    if isinstance(oauth_header, BaseModel):
        return oauth_header
    user = User(username=oauth_header)
    return user


@openapi(security=[oid])
def read_current_user(current_user: User | None = Provides()) -> Any:
    if current_user is None:
        return {"msg": "Create an account first"}
    return current_user


def test_security_oauth2():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
        enable_openapi=True,
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Bearer footokenbar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "Bearer footokenbar"}


def test_security_oauth2_password_other_header():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
        enable_openapi=True,
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Other footokenbar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "Other footokenbar"}


def test_security_oauth2_password_bearer_no_header():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
        enable_openapi=True,
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 200, response.text
        assert response.json() == {"msg": "Create an account first"}


def test_openapi_schema():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"current_user": Provide(get_current_user)},
            )
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
                        "operationId": None,
                        "summary": None,
                        "description": None,
                        "tags": None,
                        "deprecated": None,
                        "security": [
                            {
                                "OpenIdConnect": {
                                    "type": "openIdConnect",
                                    "openIdConnectUrl": "/openid",
                                    "scheme_name": "OpenIdConnect",
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
                    "OpenIdConnect": {
                        "type": "openIdConnect",
                        "openIdConnectUrl": "/openid",
                        "scheme_name": "OpenIdConnect",
                    }
                },
            },
            "servers": [{"url": "/"}],
        }
