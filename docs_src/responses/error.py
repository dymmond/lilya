from lilya.apps import Lilya
from lilya.responses import Error
from lilya.routing import Path


def home():
    return Error("<html><body><p>Error!</p></body></html>")


app = Lilya(routes=[Path("/", home)])
