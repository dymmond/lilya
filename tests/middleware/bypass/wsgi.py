from json import loads

from flask import Flask, abort

from lilya import status
from lilya.exceptions import HTTPException, NotAuthorized
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Include, Path
from lilya.testclient import create_client


def create_app():
    app = Flask(__name__)

    def handle_bad_request(e):
        return "bad request!", 400

    def handle_server_error(e):
        return "Internal server error from WSGI request!", 400

    @app.route("/")
    def index():
        abort(400, "Something went wrong!")

    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(500, handle_server_error)

    return app


async def handle_type_error(request: Request, exc: HTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    details = loads(exc.json()) if hasattr(exc, "json") else exc.args[0]
    return JSONResponse({"detail": details}, status_code=status_code)


async def lilya_return():
    return "hello"


def test_raises_error_400_in_lilya_from_wsgi(test_client_factory):
    with create_client(
        routes=[
            Include(
                path="/home",
                routes=[
                    Path("/", handler=lilya_return),
                ],
            ),
            Include(path="/api/v1", app=WSGIMiddleware(create_app(), redirect_exceptions=True)),
        ],
        exception_handlers={
            HTTPException: handle_type_error,
        },
    ) as client:
        response = client.get("/api/v1")

        assert response.status_code == 400
        assert response.json() == {"detail": "400: bad request!"}


def test_raises_error_with_custom_class(test_client_factory):
    with create_client(
        routes=[
            Include(
                path="/home",
                routes=[
                    Path("/", handler=lilya_return),
                ],
            ),
            Include(
                path="/api/v1",
                app=WSGIMiddleware(
                    create_app(), redirect_exceptions=True, exception_class=NotAuthorized
                ),
            ),
        ],
        exception_handlers={
            NotAuthorized: handle_type_error,
        },
    ) as client:
        response = client.get("/api/v1")

        assert response.status_code == 400
        assert response.json() == {"detail": "400: bad request!"}


def test_it_does_not_raise_error_400_in_lilya_from_wsgi(test_client_factory):
    with create_client(
        routes=[
            Include(
                path="/home",
                routes=[
                    Path("/", handler=lilya_return),
                ],
            ),
            Include(path="/api/v1", app=WSGIMiddleware(create_app())),
        ],
        exception_handlers={
            HTTPException: handle_type_error,
        },
    ) as client:
        response = client.get("/api/v1")
        assert response.text == "bad request!"


def test_with_flag_true_and_no_exception_handler(test_client_factory):
    with create_client(
        routes=[
            Include(
                path="/home",
                routes=[
                    Path("/", handler=lilya_return),
                ],
            ),
            Include(path="/api/v1", app=WSGIMiddleware(create_app(), redirect_exceptions=True)),
        ]
    ) as client:
        response = client.get("/api/v1")

        assert response.status_code == 400
        assert response.text == "bad request!"
