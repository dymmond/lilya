from flask import Flask, request

from lilya.apps import Lilya
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.requests import Request
from lilya.routing import Include, Path

flask_app = Flask(__name__)
second_flask_app = Flask(__name__)


@flask_app.route("/")
def flask_main():
    name = request.args.get("name", "Lilya")
    return f"Hello, {name} from your Flask integrated!"


async def home(request: Request):
    name = request.path_params["name"]
    return {"name": name}


@second_flask_app.route("/")
def second_flask_main():
    name = request.args.get("name", "Lilya")
    return f"Hello, {name} from Flask!"


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

app = Lilya(routes=routes)
