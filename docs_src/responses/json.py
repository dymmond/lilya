from lilya.app import Lilya
from lilya.responses import JSONResponse
from lilya.routing import Path


def home():
    return JSONResponse({"message": "Welcome home"})


app = Lilya(routes=[Path("/", home)])
