from lilya.app import Lilya
from lilya.requests import Request
from lilya.routing import Include, Path
from lilya.staticfiles import StaticFiles
from lilya.templating import Jinja2Template

templates = Jinja2Template(directory="templates")


async def homepage(request: Request):
    return templates.get_template_response(request, "index.html")


app = Lilya(
    debug=True,
    routes=[
        Path("/", homepage),
        Include("/static", StaticFiles(directory="static"), name="static"),
    ],
)
