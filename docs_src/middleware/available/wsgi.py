from flask import Flask, make_response

from lilya.app import Lilya
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.routing import Include

flask = Flask(__name__)


@flask.route("/home")
def home():
    return make_response({"message": "Serving via flask"})


# Add the flask app into Lilya to be served by Lilya.
routes = [Include("/external", app=WSGIMiddleware(flask))]

app = Lilya(routes=routes)
