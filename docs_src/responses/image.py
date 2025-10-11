from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import ImageResponse


async def image_download():

    # Load image bytes from a file
    with open("logo.png", "rb") as f:
        data = f.read()

    return ImageResponse(data, media_type="image/png")

app = Lilya(
    routes=[Path("/download", image_download)]
)
