from lilya.app import Lilya
from lilya.routing import Path


def home():
    return {"message": "Welcome home"}


app = Lilya(routes=[Path("/", home)])
