from typing import Any

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.http import HTTPAuthorizationCredentials, HTTPBase
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client

security = HTTPBase(scheme="Other")


@openapi(
    security=[security],
)
def read_current_user(
    credentials: HTTPAuthorizationCredentials = Provides(),
) -> Any:
    if credentials is None:
        return {"msg": "Create an account first"}
    return {"scheme": credentials.scheme, "credentials": credentials.credentials}


def test_security_http_base():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            )
        ]
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Other foobar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"scheme": "Other", "credentials": "foobar"}


def test_security_http_base_no_credentials():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            )
        ]
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
                dependencies={"credentials": Provide(security)},
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
                                "HTTPBase": {
                                    "type": "http",
                                    "scheme": "Other",
                                    "scheme_name": "HTTPBase",
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
                    "HTTPBase": {"type": "http", "scheme": "Other", "scheme_name": "HTTPBase"}
                },
            },
            "servers": [{"url": "/"}],
        }
