from lilya.routing import Path

from .views import home

route_patterns = [Path("/home", home)]
