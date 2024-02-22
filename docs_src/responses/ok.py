from lilya.apps import Lilya
from lilya.responses import Ok
from lilya.routing import Path


def home():
    return Ok({"message": "Welcome home"})


app = Lilya(routes=[Path("/", home)])
