from lilya.requests import Request
from lilya.templating import Jinja2Template


def settings_context(request: Request):
    return {"settings": request.app.settings}


templates = Jinja2Template(
    directory="templates",
    context_processors=[settings_context],
)
