import pytest

from lilya.enums import MediaType
from lilya.requests import Request
from lilya.responses import JSONResponse, Response
from lilya.routing import Include, Path, WebSocketPath
from lilya.testclient import TestClient, create_client
from lilya.websockets import WebSocket


async def allow_access() -> JSONResponse:
    return JSONResponse("Hello, world")


async def homepage() -> Response:
    return Response("Hello, world")


async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_text("Hello, world!")
    await websocket.close()


routes = [
    Path("/", handler=homepage, name="homepage"),
    Include(
        "/nested",
        routes=[
            Include(
                path="/test/",
                routes=[Path(path="/", handler=homepage, name="nested")],
            ),
            Include(
                path="/another",
                routes=[
                    Include(
                        path="/test",
                        routes=[Path(path="/{param}", handler=homepage, name="nested")],
                    )
                ],
            ),
        ],
    ),
    Include(
        "/static",
        app=Response("xxxxx", media_type=MediaType.PNG, status_code=200),
    ),
    WebSocketPath("/ws", handler=websocket_endpoint, name="websocket_endpoint"),
    Path("/allow", handler=allow_access, name="allow_access"),
]


@pytest.mark.filterwarnings(
    r"ignore"
    r":Trying to detect encoding from a tiny portion of \(5\) byte\(s\)\."
    r":UserWarning"
    r":charset_normalizer.api"
)
def test_router():
    with create_client(routes=routes) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "Hello, world"

        response = client.post("/")
        assert response.status_code == 405
        assert response.json()["detail"] == "Method POST not allowed."
        assert response.headers["content-type"] == MediaType.JSON

        response = client.get("/foo")
        assert response.status_code == 404
        assert response.json()["detail"] == "The resource cannot be found."

        response = client.get("/static/123")
        assert response.status_code == 200
        assert response.text == "xxxxx"

        response = client.get("/nested/test")
        assert response.status_code == 200
        assert response.text == "Hello, world"

        response = client.get("/nested/another/test/fluid")
        assert response.status_code == 200
        assert response.text == "Hello, world"

        with client.websocket_connect("/ws") as session:
            text = session.receive_text()
            assert text == "Hello, world!"
