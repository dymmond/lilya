from lilya.templating import Jinja2Template


def marked_filter(text): ...


templates = Jinja2Template(directory="templates")
templates.env.filters["marked"] = marked_filter
