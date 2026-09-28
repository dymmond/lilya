from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from jwt.exceptions import InvalidAudienceError, InvalidIssuerError, MissingRequiredClaimError

from lilya.contrib.security.jwt.token import Token


@freeze_time("2022-03-03")
def test_token_expiry():
    date = datetime.now()

    token = Token(exp=date)

    assert token.exp == date


def test_decode_validates_requested_audience():
    key = "shared-signing-key-at-least-32-bytes"
    expiration = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = Token(exp=expiration, sub="1", aud="service-B").encode(key, "HS256")
    token_without_audience = Token(exp=expiration, sub="1").encode(key, "HS256")

    with pytest.raises(InvalidAudienceError):
        Token.decode(token, key, ["HS256"], audience="service-A")
    with pytest.raises(InvalidAudienceError):
        Token.decode(token, key, ["HS256"], audience="service-A", options={"verify_aud": False})
    with pytest.raises(MissingRequiredClaimError):
        Token.decode(token_without_audience, key, ["HS256"], audience="service-A")

    assert Token.decode(token, key, ["HS256"], audience="service-B").sub == "1"
    assert Token.decode(token, key, ["HS256"]).aud == "service-B"
    assert Token.decode(token_without_audience, key, ["HS256"]).sub == "1"


def test_decode_validates_requested_issuer():
    key = "shared-signing-key-at-least-32-bytes"
    expiration = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = Token(exp=expiration, sub="1", iss="issuer-B").encode(key, "HS256")
    token_without_issuer = Token(exp=expiration, sub="1").encode(key, "HS256")

    with pytest.raises(InvalidIssuerError):
        Token.decode(token, key, ["HS256"], issuer="issuer-A", options={"verify_iss": False})
    with pytest.raises(MissingRequiredClaimError):
        Token.decode(token_without_issuer, key, ["HS256"], issuer="issuer-A")

    assert Token.decode(token, key, ["HS256"], issuer="issuer-B").sub == "1"
    assert Token.decode(token, key, ["HS256"]).iss == "issuer-B"
