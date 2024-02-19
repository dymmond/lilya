from myapp.accounts.urls import route_patterns

from lilya.routing import Include

route_patterns = [
    Include(routes=route_patterns),
]
