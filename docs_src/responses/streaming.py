from typing import Generator

from lilya.apps import Lilya
from lilya.responses import StreamingResponse
from lilya.routing import Path


def my_generator() -> Generator[str, None, None]:
    count = 0
    while True:
        count += 1
        yield str(count)


def home():
    return StreamingResponse(my_generator(), media_type="text/html")


app = Lilya(routes=[Path("/", home)])
