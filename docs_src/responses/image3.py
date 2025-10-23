from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import DeducingFileResponse, Response


async def image_download() -> Response:
    # this uses the file (bytes) to deduce the correct mime_type and requires python-magic
    return DeducingFileResponse("logo.png", deduce_media_type_from_body=True)


app = Lilya(
    routes=[Path("/download", image_download)]
)
