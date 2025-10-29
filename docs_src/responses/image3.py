from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import SimpleFileResponse, Response


async def image_download() -> Response:
    # this uses the file (bytes) to deduce the correct mime_type and requires python-magic
    return SimpleFileResponse("logo.png", deduce_media_type_from_body=True)


app = Lilya(
    routes=[Path("/download", image_download)]
)
