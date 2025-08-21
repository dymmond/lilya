from typing import Any

import pytest
from pydantic import BaseModel, __version__

from lilya.contrib.openapi.decorator import openapi
from lilya.contrib.security.oauth2 import OAuth2, OAuth2PasswordRequestFormStrict
from lilya.dependencies import Provide, Provides, Security
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings

pydantic_version = ".".join(__version__.split(".")[:2])

reusable_oauth2 = OAuth2(
    flows={
        "password": {
            "tokenUrl": "token",
            "scopes": {"read:users": "Read the users", "write:users": "Create users"},
        }
    },
    description="OAuth2 security scheme",
    auto_error=False,
)


class User(BaseModel):
    username: str


def get_current_user(oauth_header: str | None = Security(reusable_oauth2)):
    if oauth_header is None:
        return None
    if isinstance(oauth_header, BaseModel):
        return oauth_header
    user = User(username=oauth_header)
    return user


@openapi(
    security=[reusable_oauth2],
)
def login(form_data: OAuth2PasswordRequestFormStrict = Provides()) -> dict[str, Any]:
    return form_data


@openapi(
    security=[reusable_oauth2],
)
def read_users_me(current_user: User | None = Provides()) -> dict[str, Any]:
    if current_user is None:
        return {"msg": "Create an account first"}
    return current_user


def test_security_oauth2():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_users_me,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Bearer footokenbar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "Bearer footokenbar"}


def test_security_oauth2_password_other_header():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_users_me,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
    ) as client:
        response = client.get("/users/me", headers={"Authorization": "Other footokenbar"})
        assert response.status_code == 200, response.text
        assert response.json() == {"username": "Other footokenbar"}


def test_security_oauth2_password_bearer_no_header():
    with create_client(
        routes=[
            Path(
                "/users/me",
                handler=read_users_me,
                dependencies={"current_user": Provide(get_current_user)},
            )
        ],
    ) as client:
        response = client.get("/users/me")
        assert response.status_code == 200, response.text
        assert response.json() == {"msg": "Create an account first"}


def test_strict_login_None():
    with create_client(
        settings_module=EncoderSettings,
        routes=[
            Path(
                "/login",
                handler=login,
                methods=["POST"],
                dependencies={"form_data": Provide(OAuth2PasswordRequestFormStrict)},
            )
        ],
    ) as client:
        response = client.post("/login", data=None)
        assert response.status_code == 422

        assert response.json() == {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["grant_type"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{pydantic_version}/v/missing",
                },
                {
                    "type": "missing",
                    "loc": ["username"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{pydantic_version}/v/missing",
                },
                {
                    "type": "missing",
                    "loc": ["password"],
                    "msg": "Field required",
                    "input": {},
                    "url": f"https://errors.pydantic.dev/{pydantic_version}/v/missing",
                },
            ]
        }


def test_strict_login_no_grant_type():
    with create_client(
        routes=[
            Path(
                "/login",
                handler=login,
                methods=["POST"],
                dependencies={"form_data": Provide(OAuth2PasswordRequestFormStrict)},
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post("/login", json={"username": "johndoe", "password": "secret"})
        assert response.status_code == 422

        assert response.json() == {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["grant_type"],
                    "msg": "Field required",
                    "input": {"username": "johndoe", "password": "secret"},
                    "url": f"https://errors.pydantic.dev/{pydantic_version}/v/missing",
                }
            ]
        }


@pytest.mark.parametrize(
    argnames=["grant_type"],
    argvalues=[
        pytest.param("incorrect", id="incorrect value"),
        pytest.param("passwordblah", id="password with suffix"),
        pytest.param("blahpassword", id="password with prefix"),
    ],
)
def test_strict_login_incorrect_grant_type(grant_type):
    with create_client(
        routes=[
            Path(
                "/login",
                handler=login,
                methods=["POST"],
                dependencies={"form_data": Provide(OAuth2PasswordRequestFormStrict)},
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/login",
            json={"username": "johndoe", "password": "secret", "grant_type": grant_type},
        )
        assert response.status_code == 422
        assert response.json() == {
            "detail": [
                {
                    "type": "string_pattern_mismatch",
                    "loc": ["grant_type"],
                    "msg": "String should match pattern '^password$'",
                    "input": grant_type,
                    "ctx": {"pattern": "^password$"},
                    "url": f"https://errors.pydantic.dev/{pydantic_version}/v/string_pattern_mismatch",
                }
            ]
        }


def test_strict_login_correct_correct_grant_type():
    with create_client(
        routes=[
            Path(
                "/login",
                handler=login,
                methods=["POST"],
                dependencies={"form_data": Provide(OAuth2PasswordRequestFormStrict)},
            )
        ],
        settings_module=EncoderSettings,
    ) as client:
        response = client.post(
            "/login",
            json={"username": "johndoe", "password": "secret", "grant_type": "password"},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "grant_type": "password",
            "username": "johndoe",
            "password": "secret",
            "scopes": [],
            "client_id": None,
            "client_secret": None,
        }
