import re

from lilya._internal._crypto import get_random_secret_key
from lilya.contrib.security.csrf import (
    decode_csrf_token,
    generate_csrf_token,
    get_or_set_csrf_token,
    tokens_match,
)
from lilya.routing import Path
from lilya.testclient import create_client


def test_generate_and_decode_roundtrip():
    secret = get_random_secret_key()
    token = generate_csrf_token(secret)
    assert isinstance(token, str)

    decoded = decode_csrf_token(secret, token)

    assert decoded is not None
    assert re.fullmatch(r"[0-9a-f]{64}", decoded)


def test_tokens_match_true_false():
    secret = get_random_secret_key()
    a = generate_csrf_token(secret)
    b = a

    assert tokens_match(secret, a, b) is True

    c = generate_csrf_token(secret)

    assert tokens_match(secret, a, c) is False
    assert tokens_match(secret, a, None) is False
    assert tokens_match(secret, "", c) is False


def test_get_or_set_csrf_token_sets_cookie_and_returns_value():
    secret = get_random_secret_key()

    async def view(request):
        from lilya.responses import Ok

        response = Ok({"ok": True})
        token = get_or_set_csrf_token(
            request,
            response,
            secret,
            httponly=False,  # template-friendly
        )
        # Echo it so we can assert it equals the cookie set value
        response.headers.add("x-token", token)
        return response

    with create_client(routes=[Path("/", view, methods=["GET"])]) as client:
        response = client.get("/")
        cookie = response.cookies.get("csrftoken")

        assert cookie
        assert response.headers.get("x-token") == cookie

        # And Set-Cookie header exists
        assert "csrftoken=" in (response.headers.get("set-cookie") or "")
