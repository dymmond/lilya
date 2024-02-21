from lilya.templating import Jinja2Template

templates = Jinja2Template(
    directory="templates",
    autoescape=False,
    auto_reload=True,
)
