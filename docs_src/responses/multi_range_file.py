from lilya.apps import Lilya
from lilya.responses import FileResponse
from lilya.routing import Path


def home():
    return FileResponse(
        "files/something.csv",
        filename="something",
        range_multipart_boundary=True
    )

# or alternatively provide an explicit boundary
def home():
    return FileResponse(
        "files/something.csv",
        filename="something",
        range_multipart_boundary="1234abc"
    )



app = Lilya(routes=[Path("/", home)])
