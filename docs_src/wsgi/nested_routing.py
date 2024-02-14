from flask import Flask, request

from lilya.app import Lilya
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.requests import Request
from lilya.routing import Include, Path

flask_app = Flask(__name__)


@flask_app.route("/")
def flask_main():
    name = request.args.get("name", "Lilya")
    return f"Hello, {name} from your Flask integrated!"


async def home(request: Request):
    name = request.path_params["name"]
    return {"name": name}


app = Lilya(
    routes=[
        Path("/home/{name:str}", handler=home),
        Include(
            "/",
            routes=[
                Include("/flask", WSGIMiddleware(flask_app)),
            ],
        ),
    ]
)
