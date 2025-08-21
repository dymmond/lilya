from typing import Any

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.http import HTTPAuthorizationCredentials, HTTPDigest
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client

security = HTTPDigest()


@openapi(
    security=[security],
)
def read_current_user(credentials: HTTPAuthorizationCredentials = Provides()) -> Any:
    return {"scheme": credentials.scheme, "credentials": credentials.credentials}


def test_security_http_digest():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Digest foobar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"scheme": "Digest", "credentials": "foobar"}


def test_security_http_digest_no_credentials():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 403, response.text
        assert response.text == "Not authenticated"


def test_security_http_digest_incorrect_scheme_credentials():
    with create_client(
        routes=[
            Path("/users/me", read_current_user, dependencies={"credentials": Provide(security)})
        ]
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Other invalidauthorization"})
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
                        "security": [
                            {
                                "HTTPDigest": {
                                    "type": "http",
                                    "scheme": "digest",
                                    "scheme_name": "HTTPDigest",
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
                    "HTTPDigest": {"type": "http", "scheme": "digest", "scheme_name": "HTTPDigest"}
                },
            },
            "servers": [{"url": "/"}],
        }
