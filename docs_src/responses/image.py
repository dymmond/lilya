from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import DeducingFileResponse, Response


async def image_download() -> Response:

    # Load image bytes from a file
    with open("logo.png", "rb") as f:
        data = f.read()

    # this uses an explicit specified media type and doesn't use python magic
    return DeducingFileResponse(data, media_type="image/png")


app = Lilya(
    routes=[Path("/download", image_download)]
)
