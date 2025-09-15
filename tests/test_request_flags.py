import pytest

from lilya.requests import Request
from lilya.types import Scope

pytestmark = pytest.mark.anyio


async def test_is_json_flag(test_client_factory):
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/json")],
    }
    request = Request(scope)

    assert request.is_json is True
    assert request.is_form is False


async def test_is_form_urlencoded_flag(test_client_factory):
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }
    request = Request(scope)

    assert request.is_form is True
    assert request.is_json is False


async def test_is_form_multipart_flag(test_client_factory):
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"multipart/form-data; boundary=----test")],
    }
    request = Request(scope)

    assert request.is_form is True
    assert request.is_json is False


async def test_is_neither_json_nor_form(test_client_factory):
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"text/plain")],
    }
    request = Request(scope)

    assert request.is_json is False
    assert request.is_form is False
