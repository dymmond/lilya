from __future__ import annotations

from collections.abc import Callable

import pytest

from lilya.apps import Lilya
from lilya.responses import Response
from lilya.testclient import TestClient

app = Lilya()


@app.get("/")
async def homepage():
    return Response("Hello, world", media_type="text/plain")


@app.get("/users")
async def users():
    return Response("All users", media_type="text/plain")


@app.post("/users")
def create_users():
    return Response("User created", media_type="text/plain")


@app.route("/generic", methods=["DELETE", "POST"])
async def generic():
    return Response("Generic route", media_type="text/plain")


@app.route("/params/{name}/<age:int>", methods=["GET", "POST"])
async def params(name: str, age: int):
    return Response(f"Name {name} with age {age}", media_type="text/plain")


@pytest.fixture
def client(test_client_factory: Callable[..., TestClient]):
    with test_client_factory(app) as client:
        yield client


def test_decorators(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, world"

    response = client.get("/users")
    assert response.status_code == 200
    assert response.text == "All users"

    response = client.post("/users")
    assert response.status_code == 200
    assert response.text == "User created"

    response = client.post("/generic")
    assert response.status_code == 200
    assert response.text == "Generic route"

    response = client.delete("/generic")
    assert response.status_code == 200
    assert response.text == "Generic route"

    response = client.get("/generic")
    assert response.status_code == 405

    response = client.get("/params/John/20")
    assert response.status_code == 200
    assert response.text == "Name John with age 20"

    response = client.post("/params/John/20")
    assert response.status_code == 200
    assert response.text == "Name John with age 20"
