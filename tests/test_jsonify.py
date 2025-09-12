import pytest

from lilya.apps import Lilya
from lilya.contrib.responses.json import jsonify
from lilya.routing import Path
from lilya.testclient import TestClient


def test_jsonify_with_kwargs(test_client_factory):
    async def endpoint():
        return jsonify(message="Hello", status="ok")

    app = Lilya(routes=[Path("/json", endpoint)])
    client = TestClient(app)

    response = client.get("/json")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello", "status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_jsonify_with_single_arg_list(test_client_factory):
    async def endpoint(request):
        return jsonify([1, 2, 3])

    app = Lilya(routes=[Path("/list", endpoint)])
    client = TestClient(app)

    response = client.get("/list")
    assert response.status_code == 200
    assert response.json() == [1, 2, 3]


def test_jsonify_with_multiple_args(test_client_factory):
    async def endpoint():
        return jsonify(1, 2, 3)

    app = Lilya(routes=[Path("/multi", endpoint)])
    client = TestClient(app)

    response = client.get("/multi")
    assert response.status_code == 200
    assert response.json() == [1, 2, 3]


def test_jsonify_with_custom_status_code(test_client_factory):
    async def endpoint(request):
        return jsonify(message="created", status_code=201)

    app = Lilya(routes=[Path("/created", endpoint)])
    client = TestClient(app)

    response = client.get("/created")
    assert response.status_code == 201
    assert response.json() == {"message": "created"}


def test_jsonify_with_headers(test_client_factory):
    async def endpoint():
        return jsonify(message="Hello", headers={"X-Custom": "value"})

    app = Lilya(routes=[Path("/headers", endpoint)])
    client = TestClient(app)

    response = client.get("/headers")
    assert response.status_code == 200
    assert response.headers["x-custom"] == "value"
    assert response.json() == {"message": "Hello"}


def test_jsonify_with_cookies(test_client_factory):
    async def endpoint():
        return jsonify(message="Hello", cookies={"session": "abc123"})

    app = Lilya(routes=[Path("/cookies", endpoint)])
    client = TestClient(app)

    response = client.get("/cookies")
    assert response.status_code == 200
    assert "set-cookie" in response.headers
    assert response.headers["set-cookie"].startswith("session=abc123")
    assert response.json() == {"message": "Hello"}


def test_jsonify_raises_on_args_and_kwargs(test_client_factory):
    async def endpoint():
        with pytest.raises(TypeError):
            return jsonify({"a": 1}, b=2)

    app = Lilya(routes=[Path("/error", endpoint)])
    client = TestClient(app)

    # since exception is raised inside endpoint, Lilya will return 500
    response = client.get("/error")
    assert response.status_code == 500
