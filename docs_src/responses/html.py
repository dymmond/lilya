from lilya.app import Lilya
from lilya.responses import HTMLResponse
from lilya.routing import Path


def home():
    return HTMLResponse("<html><body><p>Welcome!</p></body></html>")


app = Lilya(routes=[Path("/", home)])
