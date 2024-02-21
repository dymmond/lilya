from flask import Flask, request
from markupsafe import escape

from lilya.apps import ChildLilya, Lilya
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.testclient import create_client

flask_app = Flask(__name__)


@flask_app.route("/")
def flask_main():
    name = request.args.get("name", "Lilya")
    return f"Hello, {escape(name)} from Flask!"


async def home(request: Request):
    name = request.path_params["name"]
    return {"name": name}


def test_serve_flask_via_esmerald(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include("/flask", WSGIMiddleware(flask_app)),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_flask_via_nested_include(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include(
            "/",
            routes=[
                Include("/flask", WSGIMiddleware(flask_app)),
            ],
        ),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_flask_via_deep_nested_include(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include(
            "/",
            routes=[
                Include(
                    "/",
                    routes=[
                        Include(
                            "/",
                            routes=[
                                Include(
                                    "/",
                                    routes=[
                                        Include(
                                            "/",
                                            routes=[
                                                Include(
                                                    "/",
                                                    routes=[
                                                        Include(
                                                            "/flask",
                                                            WSGIMiddleware(flask_app),
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


second_flask_app = Flask(__name__)


@second_flask_app.route("/")
def second_flask_main():
    name = request.args.get("name", "Lilya")
    return f"Hello, {escape(name)} from Flask!"


def test_serve_more_than_one_flask_app_via_esmerald(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include("/flask", WSGIMiddleware(flask_app)),
        Include("/second/flask", WSGIMiddleware(second_flask_app)),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_more_than_one_flask_app_via_esmerald_two(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include("/flask", WSGIMiddleware(flask_app)),
        Include("/second/flask", WSGIMiddleware(second_flask_app)),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_more_than_one_flask_app_via_nested_include(test_client_factory):
    routes = [
        Path("/home/{name:str}", handler=home),
        Include(
            "/",
            routes=[
                Include(
                    "/internal",
                    routes=[
                        Include(
                            "/",
                            routes=[
                                Include("/flask", WSGIMiddleware(flask_app)),
                            ],
                        )
                    ],
                ),
                Include(
                    "/",
                    routes=[
                        Include(
                            "/",
                            routes=[
                                Include(
                                    "/external",
                                    routes=[
                                        Include(
                                            "/second/flask",
                                            WSGIMiddleware(second_flask_app),
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                ),
            ],
        ),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/internal/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/external/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_routes_inder_main_path(test_client_factory):
    routes = [
        Include(
            path="/",
            routes=[
                Path("/home/{name:str}", handler=home),
                Include("/flask", WSGIMiddleware(flask_app)),
                Include("/second/flask", WSGIMiddleware(second_flask_app)),
            ],
        )
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_routes_inder_main_path_with_different_names(test_client_factory):
    routes = [
        Include(
            path="/api/v1",
            routes=[
                Path("/home/{name:str}", handler=home),
                Include(
                    "/ext/v2",
                    routes=[
                        Include("/flask", WSGIMiddleware(flask_app)),
                        Include("/second/flask", WSGIMiddleware(second_flask_app)),
                    ],
                ),
            ],
        )
    ]

    with create_client(routes=routes) as client:
        response = client.get("/api/v1/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/api/v1/ext/v2/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/api/v1/ext/v2/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_under_another_lilya_app(test_client_factory):
    lilya_app = Lilya(
        routes=[
            Path("/home/{name:str}", home),
            Include("/flask", WSGIMiddleware(flask_app)),
            Include("/second/flask", WSGIMiddleware(second_flask_app)),
        ]
    )

    routes = [
        Include("/lilya", lilya_app),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/lilya/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/lilya/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/lilya/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"


def test_serve_under_another_lilya_app_two(test_client_factory):
    lilya_app = ChildLilya(
        routes=[
            Path("/home/{name:str}", home),
            Include("/flask", WSGIMiddleware(flask_app)),
            Include("/second/flask", WSGIMiddleware(second_flask_app)),
        ]
    )

    routes = [
        Path("/home/{name:str}", home),
        Include("/lilya", lilya_app),
        Path("/test/home/{name:str}", handler=home),
    ]

    with create_client(routes=routes) as client:
        response = client.get("/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/test/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/lilya/home/lilya")
        assert response.status_code == 200
        assert response.json() == {"name": "lilya"}

        response = client.get("/lilya/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"

        response = client.get("/lilya/second/flask")
        assert response.status_code == 200
        assert response.text == "Hello, Lilya from Flask!"
