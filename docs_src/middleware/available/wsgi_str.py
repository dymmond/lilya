from flask import Flask, make_response

flask = Flask(__name__)


@flask.route("/home")
def home():
    return make_response({"message": "Serving via flask"})
