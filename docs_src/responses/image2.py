from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import SimpleFileResponse, Response


async def image_download() -> Response:
    # this uses the file name to deduce the file type and
    # doesn't! require python-magic
    return SimpleFileResponse("logo.png")


app = Lilya(
    routes=[Path("/download", image_download)]
)
