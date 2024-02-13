from lilya.app import Lilya
from lilya.responses import make_response
from lilya.routing import Path


def home():
    return make_response({{"message": "Hello"}}, status_code=201)


app = Lilya(routes=[Path("/", home)])
