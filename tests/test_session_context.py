import pytest

from lilya.apps import Lilya
from lilya.context import session
from lilya.middleware import DefineMiddleware
from lilya.middleware.session_context import SessionContextMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request
from lilya.routing import Path
from lilya.testclient import TestClient


async def home(request: Request) -> dict:
    assert session._session_getter() is request.scope["session"]["foo"]
    session["visits"] = session.get("visits", 0) + 1
    return {"visits": session["visits"]}


async def reset():
    session.reset_context()


def create_app() -> Lilya:
    app = Lilya(
        routes=[
            Path("/", home),
            Path(
                "/reset",
                reset,
                middleware=[DefineMiddleware(SessionContextMiddleware, sub_path="foo")],
            ),
        ],
        middleware=[
            DefineMiddleware(SessionMiddleware, secret_key="your-secret-key"),
            DefineMiddleware(SessionContextMiddleware, sub_path="foo"),
        ],
    )

    return app


# Initialize the client
@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as client:
        yield client


# Test 1: Check if session is initialized and incremented correctly
def test_session_increment(client):
    # Make a request, this should increment the visits count to 1
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"visits": 1}

    # Make another request, this should increment the visits count to 2
    response = client.get("/")
    assert response.json() == {"visits": 2}


# Test 2: Check if session persists data across requests (using session["visits"])
def test_session_persistence(client):
    # First request - session should be initialized to 1
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["visits"] == 1

    # Second request - session should increment to 2
    response = client.get("/")
    assert response.json()["visits"] == 2

    # Third request - session should increment to 3
    response = client.get("/")
    assert response.json()["visits"] == 3


def test_session_get_default_value(client):
    # Make a request without setting any session data
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["visits"] == 1

    # Check for a non-existent key, it should return the default value
    response = client.get("/non_existent_key")
    assert response.status_code == 404


def test_session_reset(client):
    # First request - session should be initialized
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["visits"] == 1  # Session is initialized to 1 on first visit

    # Increment session visits to 2
    response = client.get("/")
    assert response.json()["visits"] == 2

    # Reset the session
    response = client.get("/reset")
    assert any(
        "expires=Thu, 01 Jan 1970 00:00:00 GMT" in h
        for h in response.headers.get_list("Set-Cookie")
    )

    # Make another request after resetting the session - should be reset
    response = client.get("/")
    assert response.json()["visits"] == 1  # Session should be reset to 1 again

    # Increment session visits again to 2 after reset
    response = client.get("/")
    assert response.json()["visits"] == 2

    # Reset again
    client.get("/reset")

    # Ensure the session is reset again
    response = client.get("/")
    assert response.json()["visits"] == 1  # Should be reset to 1 again
