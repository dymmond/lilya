from base64 import b64encode
from typing import Any

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.http import HTTPBasic, HTTPBasicCredentials
from lilya.dependencies import Provide, Provides
from lilya.routing import Path
from lilya.testclient import create_client

security = HTTPBasic(realm="simple")


@openapi(
    security=[security],
)
def read_current_user(credentials: HTTPBasicCredentials | None = Provides()) -> Any:
    if credentials is None:
        return {"msg": "Create an account first"}
    return {"username": credentials.username, "password": credentials.password}


def test_security_http_basic():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            ),
        ],
    ) as client:
        response = client.get("/users/me", auth=("john", "secret"))
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "john", "password": "secret"}


def test_security_http_basic_no_credentials():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            ),
        ],
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 401, response.text
        assert response.headers["WWW-Authenticate"] == 'Basic realm="simple"'
        assert response.text == "Not authenticated"


def test_security_http_basic_invalid_credentials():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            ),
        ],
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Basic notabase64token"})
        assert response.status_code == 401, response.text
        assert response.headers["WWW-Authenticate"] == 'Basic realm="simple"'
        assert response.text == "Invalid authentication credentials"


def test_security_http_basic_non_basic_credentials():
    payload = b64encode(b"johnsecret").decode("ascii")
    auth_header = f"Basic {payload}"

    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            ),
        ],
    ) as client:
        response = client.get("/users/me", headers={"Authorization": auth_header})
        assert response.status_code == 401, response.text
        assert response.headers["WWW-Authenticate"] == 'Basic realm="simple"'
        assert response.text == "Invalid authentication credentials"


def test_openapi_schema():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_current_user,
                dependencies={"credentials": Provide(security)},
            ),
        ],
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
                                "HTTPBasic": {
                                    "type": "http",
                                    "scheme": "basic",
                                    "scheme_name": "HTTPBasic",
                                    "realm": "simple",
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
                    "HTTPBasic": {
                        "type": "http",
                        "scheme": "basic",
                        "scheme_name": "HTTPBasic",
                        "realm": "simple",
                    }
                },
            },
            "servers": [{"url": "/"}],
        }
