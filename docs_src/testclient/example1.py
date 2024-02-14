from lilya.responses import HTMLResponse
from lilya.testclient import TestClient


async def app(scope, receive, send):
    assert scope["type"] == "http"
    response = HTMLResponse("<html><body>Hello, world!</body></html>")
    await response(scope, receive, send)


def test_application():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
