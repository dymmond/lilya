from lilya.responses import HTMLResponse
from lilya.testclient import AsyncTestClient


async def app(scope, receive, send):
    assert scope["type"] == "http"
    response = HTMLResponse("<html><body>Hello, world!</body></html>")
    await response(scope, receive, send)


async def test_application():
    client = AsyncTestClient(app)
    response = await client.get("/")
    assert response.status_code == 200
