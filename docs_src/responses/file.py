from lilya.apps import Lilya
from lilya.responses import FileResponse
from lilya.routing import Path


def home():
    return FileResponse(
        "files/something.csv",
        filename="something",
    )


app = Lilya(routes=[Path("/", home)])
