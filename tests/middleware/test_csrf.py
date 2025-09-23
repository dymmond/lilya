import pytest

from lilya import status
from lilya._internal._crypto import get_random_secret_key
from lilya.exceptions import PermissionDenied
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware
from lilya.responses import Ok
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


# Helper to build a minimal multipart/form-data body
def make_multipart(fields: dict[str, str], boundary: str = "----pytestboundary"):
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        )
    parts.append(f"--{boundary}--\r\n")
    body = "".join(parts).encode("utf-8")
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


async def read_form_handler(request):
    # Ensures the handler can still read the body after the middleware consumed it
    form = await request.form()

    # Return whatever we parsed so tests can assert on it
    return Ok({"received": dict(form)})


async def read_body_handler(request):
    # read raw body (useful to assert replay works at the byte level)
    body = await request.body()
    return Ok({"length": len(body)})


def test_csrf_form_urlencoded_success(test_client_factory) -> None:
    with create_client(
        routes=[
            Path(path="/", handler=read_form_handler, methods=["GET", "POST"]),
        ],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
    ) as client:
        # Set cookie
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        token = response.cookies.get("csrftoken")

        assert token

        # Submit classic urlencoded form with csrf_token field (no header)
        body = f"username=alice&csrf_token={token}"

        response2 = client.post(
            "/",
            headers={"content-type": "application/x-www-form-urlencoded"},
            content=body.encode("utf-8"),
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["received"]["username"] == "alice"
        assert response2.json()["received"]["csrf_token"] == token


def test_csrf_form_urlencoded_missing_token_fails(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        body = "username=alice"

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.post(
                "/",
                headers={"content-type": "application/x-www-form-urlencoded"},
                content=body.encode("utf-8"),
            )


def test_csrf_form_urlencoded_mismatched_token_fails(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        token = response.cookies.get("csrftoken")

        assert token

        body = f"username=alice&csrf_token={token}INVALID"

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.post(
                "/",
                headers={"content-type": "application/x-www-form-urlencoded"},
                content=body.encode("utf-8"),
            )


def test_csrf_multipart_success(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        token = response.cookies.get("csrftoken")

        assert token

        body, content_type = make_multipart({"username": "bob", "csrf_token": token})
        response2 = client.post("/", headers={"content-type": content_type}, content=body)

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["received"]["username"] == "bob"
        assert response2.json()["received"]["csrf_token"] == token


def test_csrf_multipart_missing_token_fails(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        body, content_type = make_multipart({"username": "bob"})

        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.post("/", headers={"content-type": content_type}, content=body)


def test_csrf_multipart_mismatched_token_fails(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        token = response.cookies.get("csrftoken")

        assert token

        body, content_type = make_multipart({"username": "bob", "csrf_token": token + "bad"})
        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.post("/", headers={"content-type": content_type}, content=body)


def test_csrf_form_fallback_allows_handler_to_read_body(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
    ) as client:
        response = client.get("/")

        assert response.status_code == HTTP_200_OK

        token = response.cookies.get("csrftoken")

        assert token

        # No header; middleware must parse csrf_token from the body.
        body = f"foo=bar&csrf_token={token}"
        response2 = client.post(
            "/",
            headers={"content-type": "application/x-www-form-urlencoded"},
            content=body.encode("utf-8"),
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["received"] == {"foo": "bar", "csrf_token": token}


def test_csrf_form_fallback_allows_handler_to_read_raw_body(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_body_handler, methods=["GET", "POST"])],
        middleware=[DefineMiddleware(CSRFMiddleware, secret=get_random_secret_key())],
    ) as client:
        response = client.get("/")
        token = response.cookies.get("csrftoken")
        body = f"foo=bar&csrf_token={token}".encode()

        response2 = client.post(
            "/",
            headers={"content-type": "application/x-www-form-urlencoded"},
            content=body,
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["length"] == len(body)


def test_csrf_custom_form_field_name(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[
            DefineMiddleware(
                CSRFMiddleware,
                secret=get_random_secret_key(),
                form_field_name="csrfmiddlewaretoken",  # Django-like name
            )
        ],
    ) as client:
        response = client.get("/")
        token = response.cookies.get("csrftoken")

        assert token

        body = f"username=carol&csrfmiddlewaretoken={token}"
        response2 = client.post(
            "/",
            headers={"content-type": "application/x-www-form-urlencoded"},
            content=body.encode("utf-8"),
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["received"]["username"] == "carol"

        # The handler still sees the custom field (middleware only reads/compares it)
        assert response2.json()["received"]["csrfmiddlewaretoken"] == token


def test_csrf_form_fallback_respects_max_body_size(test_client_factory) -> None:
    with create_client(
        routes=[Path(path="/", handler=read_form_handler, methods=["GET", "POST"])],
        middleware=[
            DefineMiddleware(
                CSRFMiddleware,
                secret=get_random_secret_key(),
                max_body_size=10,  # very small cap to trigger the guard
            )
        ],
        enable_intercept_global_exceptions=False,
    ) as client:
        response = client.get("/")
        token = response.cookies.get("csrftoken")

        assert token

        # Body larger than 10 bytes; middleware will refuse to parse fallback token
        body = ("x" * 20) + f"&csrf_token={token}"
        with pytest.raises(PermissionDenied, match="CSRF token verification failed."):
            client.post(
                "/",
                headers={"content-type": "application/x-www-form-urlencoded"},
                content=body.encode("utf-8"),
            )
