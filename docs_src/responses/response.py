from lilya.app import Lilya
from lilya.responses import Response
from lilya.routing import Path


def home():
    return Response("Welcome home")


app = Lilya(routes=[Path("/", home)])
