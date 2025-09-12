import pytest

from lilya import status
from lilya._internal._crypto import get_random_secret_key
from lilya.exceptions import PermissionDenied
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware
from lilya.routing import Path, WebSocketPath
from lilya.status import HTTP_200_OK
from lilya.testclient import create_client
from lilya.websockets import WebSocket


def get_handler() -> None: ...


def test_csrf_successful_flow() -> None:
    with create_client(
        routes=[
            Path(path="/", handler=get_handler, methods=["GET", "POST", "PUT"]),
        ],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token = response.cookies.get("csrftoken")
        assert csrf_token is not None

        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert set_cookie_header.split("; ") == [
            f"csrftoken={csrf_token}",
            "Path=/",
            "SameSite=lax",
        ]

        response = client.post("/", headers={"x-csrftoken": csrf_token})
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "DELETE", "PATCH"],
)
def test_unsafe_method_fails_without_csrf_header_with_enable_intercept_global_exceptions_false(
    method: str,
) -> None:
    with create_client(
        routes=[
            Path(path="/", handler=get_handler, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
        ],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token = response.cookies.get("csrftoken")  # type: ignore[no-untyped-call]
        assert csrf_token is not None

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.request(method, "/")


def test_invalid_csrf_token() -> None:
    with create_client(
        routes=[
            Path(path="/", handler=get_handler, methods=["get", "post"]),
        ],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token = response.cookies.get("csrftoken")  # type: ignore[no-untyped-call]
        assert csrf_token is not None

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            response = client.post("/", headers={"x-csrftoken": csrf_token + "invalid"})


def test_csrf_token_too_short() -> None:
    with create_client(
        routes=[
            Path(path="/", handler=get_handler, methods=["GET", "post"]),
        ],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert "csrftoken" in response.cookies

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            response = client.post("/", headers={"x-csrftoken": "too-short"})


def test_websocket_ignored() -> None:
    async def websocket_handler(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json({"data": "123"})
        await websocket.close()

    with (
        create_client(
            routes=[WebSocketPath(path="/", handler=websocket_handler)],
            middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        ) as client,
        client.websocket_connect("/") as ws,
    ):
        response = ws.receive_json()
        assert response is not None


def test_custom_csrf_config() -> None:
    with create_client(
        base_url="http://test.com",
        routes=[
            Path(path="/", handler=get_handler, methods=["GET", "post"]),
        ],
        middleware=[
            DefineMiddleware(
                CSRFMiddleware,
                secret=get_random_secret_key(),
                cookie_name="custom-csrftoken",
                header_name="x-custom-csrftoken",
            )
        ],
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token = response.cookies.get("custom-csrftoken")  # type: ignore[no-untyped-call]
        assert csrf_token is not None

        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert set_cookie_header.split("; ") == [
            f"custom-csrftoken={csrf_token}",
            "Path=/",
            "SameSite=lax",
        ]

        response = client.post("/", headers={"x-custom-csrftoken": csrf_token})
        assert response.status_code == HTTP_200_OK
