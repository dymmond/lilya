from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path
from lilya.testclient import TestClient


def home():
    return Ok(
        {"detail": "welcome home"},
    )


def home_with_request(request: Request):
    return Ok(request.path_params)


def test_path():
    path = Path(path="/test/{name}", handler=home)

    client = TestClient(path)
    response = client.get("test/lilya")

    assert response.status_code == 200
    assert response.json() == {"detail": "welcome home"}


def test_path_with_request():
    path = Path(path="/test/{name}", handler=home_with_request)

    client = TestClient(path)
    response = client.get("test/lilya")

    assert response.status_code == 200
    assert response.json() == {"name": "lilya"}
