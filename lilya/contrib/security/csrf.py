from __future__ import annotations

import hashlib
import hmac
import secrets
from secrets import compare_digest
from typing import Literal

from lilya.datastructures import Cookie
from lilya.requests import Request
from lilya.responses import Response

# Keep these in sync with CSRFMiddleware
CSRF_SECRET_BYTES = 32
CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


def generate_csrf_token(secret: str) -> str:
    """
    Generate a CSRF token (double-submit cookie pattern) compatible with CSRFMiddleware.

    Structure:
      <random_hex[64]> + <hmac_sha256_hex_of_random_with_secret>

    Returns the *full* token string that should be placed in the cookie and compared
    with the submitted value (header or form field).
    """
    token_secret = secrets.token_hex(CSRF_SECRET_BYTES)
    token_hash = hmac.new(secret.encode(), token_secret.encode(), hashlib.sha256).hexdigest()
    return token_secret + token_hash


def decode_csrf_token(secret: str, token: str) -> str | None:
    """
    Validate a CSRF token and return the random secret part if valid, else None.
    """
    if not token or len(token) < CSRF_SECRET_LENGTH + 1:
        return None
    token_secret = token[:CSRF_SECRET_LENGTH]
    existing_hash = token[CSRF_SECRET_LENGTH:]
    expected_hash = hmac.new(secret.encode(), token_secret.encode(), hashlib.sha256).hexdigest()
    if not compare_digest(existing_hash, expected_hash):
        return None
    return token_secret


def tokens_match(secret: str, a: str | None, b: str | None) -> bool:
    """
    Return True iff both tokens are valid (HMAC) and their decoded secrets match.
    """
    if not a or not b:
        return False
    da = decode_csrf_token(secret, a)
    db = decode_csrf_token(secret, b)
    return (da is not None) and (db is not None) and compare_digest(da, db)


def build_csrf_cookie(
    secret: str,
    *,
    cookie_name: str = "csrftoken",
    path: str = "/",
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] = "lax",
    domain: str | None = None,
) -> Cookie:
    """
    Build a Set-Cookie object carrying a fresh CSRF token.
    """
    value = generate_csrf_token(secret)
    return Cookie(
        key=cookie_name,
        value=value,
        path=path,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        domain=domain,
    )


def ensure_csrf_cookie(
    secret: str,
    *,
    response: Response | None = None,
    cookie_name: str = "csrftoken",
    path: str = "/",
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] = "lax",
    domain: str | None = None,
) -> str:
    """
    Add a CSRF cookie to the response (if you need it *now*) and return the token value.

    Useful for first-time GETs where the template needs the token in a hidden input
    and you don't want to rely on middleware to set the cookie later.
    """
    cookie = build_csrf_cookie(
        secret,
        cookie_name=cookie_name,
        path=path,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        domain=domain,
    )

    if response:
        # The Response in Lilya has a header map supporting .add()
        response.headers.add("set-cookie", cookie.to_header(header=""))
    return cookie.value


def get_or_set_csrf_token(
    request: Request,
    secret: str,
    *,
    response: Response | None = None,
    cookie_name: str = "csrftoken",
    path: str = "/",
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] = "lax",
    domain: str | None = None,
) -> str:
    """
    Return the existing CSRF cookie value if present, otherwise set a new cookie and return it.

    This is the ergonomic helper to call from GET handlers that render a form.
    If the client already has a CSRF cookie, re-use it; otherwise create one *now*
    and return its value for your template.
    """
    existing = request.cookies.get(cookie_name)

    if existing:
        return existing
    return ensure_csrf_cookie(
        secret,
        response=response,
        cookie_name=cookie_name,
        path=path,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        domain=domain,
    )
