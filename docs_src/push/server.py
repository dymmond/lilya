from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import HTMLResponse
from lilya.routing import Include, Path
from lilya.staticfiles import StaticFiles


async def homepage(request: Request):
    """
    Handler featuring server push for delivering the stylesheet.
    """
    await request.send_push_promise("/static/app.css")
    return HTMLResponse(
        '<html><head><link rel="stylesheet" href="/static/app.css"/></head></html>'
    )


app = Lilya(
    routes=[
        Path("/", homepage),
        Include("/static", StaticFiles(directory="static"), name="static"),
    ]
)
