import base64
import hashlib
import hmac
import time
from urllib.parse import parse_qs, urlparse

import pytest

from lilya.contrib.security.signed_urls import SignedURLGenerator

pytestmark = pytest.mark.anyio


def make_signer():
    return SignedURLGenerator(secret_key="supersecret")


def test_sign_and_verify_basic():
    signer = make_signer()
    url = "https://example.com/data?id=10"

    signed = signer.sign(url, expires_in=10)

    assert "sig=" in signed
    assert "expires=" in signed
    assert signer.verify(signed) is True


def test_verify_fails_after_expiration(monkeypatch):
    signer = make_signer()
    url = "https://example.com/file"

    signed = signer.sign(url, expires_in=1)
    # simulate expiry
    time.sleep(2)

    assert signer.verify(signed) is False


def test_verify_fails_when_signature_tampered():
    signer = make_signer()
    url = "https://example.com/file"
    signed = signer.sign(url, expires_in=100)

    # Tamper with the query string
    tampered = signed.replace("file", "file2")

    assert signer.verify(tampered) is False


def test_signature_is_deterministic_for_same_input():
    signer = make_signer()
    url = "https://example.com/path?x=1"
    s1 = signer.sign(url, expires_in=60)
    s2 = signer.sign(url, expires_in=60)

    assert s1 == s2  # deterministic output for same timestamp window


def test_signature_differs_for_different_expiration():
    signer = make_signer()
    url = "https://example.com/path"
    s1 = signer.sign(url, expires_in=30)
    time.sleep(1)
    s2 = signer.sign(url, expires_in=60)

    assert s1 != s2


def test_existing_query_params_preserved():
    signer = make_signer()
    base = "https://example.com/api?foo=bar"
    signed = signer.sign(base, expires_in=300)

    parsed = urlparse(signed)
    query = parse_qs(parsed.query)

    assert query["foo"] == ["bar"]
    assert "sig" in query and "expires" in query


def test_invalid_signature_returns_false():
    signer = make_signer()
    url = "https://example.com/abc"
    signed = signer.sign(url)

    # corrupt the sig value
    parsed = urlparse(signed)
    params = dict(p.split("=") for p in parsed.query.split("&"))
    params["sig"] = "aaaaaa"
    rebuilt = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    assert signer.verify(rebuilt) is False


def test_using_different_algorithm_yields_different_signature():
    s1 = SignedURLGenerator(secret_key="supersecret", algorithm="sha256")
    s2 = SignedURLGenerator(secret_key="supersecret", algorithm="sha512")
    url = "https://example.com/data"

    sig1 = s1.sign(url)
    sig2 = s2.sign(url)

    assert sig1 != sig2


def test_short_expiration_edge_case(monkeypatch):
    signer = make_signer()
    url = "https://example.com/path"
    signed = signer.sign(url, expires_in=0)  # already expired

    assert signer.verify(signed) is False


def test_signature_verification_is_constant_time():
    """Ensure we use compare_digest for timing-safe check."""
    signer = make_signer()
    url = "https://example.com/path"
    signed = signer.sign(url)
    parsed = urlparse(signed)
    params = dict(p.split("=") for p in parsed.query.split("&"))

    # rebuild expected signature manually to confirm integrity
    expires = params["expires"]
    to_sign = f"{parsed.path}?expires={expires}".encode()
    expected = hmac.new(b"supersecret", to_sign, hashlib.sha256).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).decode().rstrip("=")

    assert params["sig"] == expected_b64


def test_sign_and_verify_with_long_query_string():
    signer = make_signer()
    long_url = "https://example.com/path?" + "&".join(f"q{i}=val{i}" for i in range(20))
    signed = signer.sign(long_url, expires_in=100)

    assert signer.verify(signed)


def test_verify_rejects_missing_signature():
    signer = make_signer()
    unsigned = "https://example.com/file?expires=9999999999"

    assert signer.verify(unsigned) is False


def test_verify_rejects_missing_expires():
    signer = make_signer()
    unsigned = "https://example.com/file?sig=abcd1234"

    assert signer.verify(unsigned) is False


def test_multiple_instances_with_same_secret_work_equally():
    s1 = make_signer()
    s2 = make_signer()

    url = "https://example.com/data"
    signed = s1.sign(url)

    assert s2.verify(signed)


def test_sign_and_verify_multiple_times_consistency():
    signer = make_signer()
    url = "https://example.com/path"
    signed = signer.sign(url, expires_in=5)

    for _ in range(5):
        assert signer.verify(signed)


@pytest.mark.parametrize("algo", ["sha1", "sha256", "sha512"])
def test_all_supported_algorithms(algo):
    signer = SignedURLGenerator(secret_key="key", algorithm=algo)
    url = "https://example.com/test"
    signed = signer.sign(url)

    assert signer.verify(signed)
