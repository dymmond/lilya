from lilya.app import Lilya
from lilya.responses import RedirectResponse
from lilya.routing import Path


def home():
    return RedirectResponse(url="/another-url")


app = Lilya(routes=[Path("/", home)])
