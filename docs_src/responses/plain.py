from lilya.app import Lilya
from lilya.responses import PlainText
from lilya.routing import Path


def home():
    return PlainText("Welcome home")


app = Lilya(routes=[Path("/", home)])
