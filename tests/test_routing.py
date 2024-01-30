from lilya.responses import Ok
from lilya.routing import Path
from lilya.testclient import TestClient


def home():
    return Ok(
        {"detail": "welcome home"},
    )


def xtest_path():
    path = Path(path="/test/{name}", handler=home)

    client = TestClient(path)
    breakpoint()
    response = client.get("test/tiago")

    assert response.status_code == 200
