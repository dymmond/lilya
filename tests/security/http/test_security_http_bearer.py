from typing import Any

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.http import HTTPAuthorizationCredentials, HTTPBearer
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client

security = HTTPBearer()


@openapi(
    security=[security],
)
def read_current_user(credentials: HTTPAuthorizationCredentials = Provides()) -> Any:
    return {"scheme": credentials.scheme, "credentials": credentials.credentials}


def test_security_http_bearer():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Bearer foobar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"scheme": "Bearer", "credentials": "foobar"}


def test_security_http_bearer_no_credentials():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 403, response.text
        assert response.text == "Not authenticated"


def test_security_http_bearer_incorrect_scheme_credentials():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Basic notreally"})
        assert response.status_code == 403, response.text
        assert response.text == "Invalid authentication credentials"


def test_openapi_schema():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
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
                                "HTTPBearer": {
                                    "type": "http",
                                    "scheme": "bearer",
                                    "scheme_name": "HTTPBearer",
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
                    "HTTPBearer": {"type": "http", "scheme": "bearer", "scheme_name": "HTTPBearer"}
                },
            },
            "servers": [{"url": "/"}],
        }
