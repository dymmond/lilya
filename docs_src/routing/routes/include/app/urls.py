from lilya.apps import Lilya
from lilya.routing import Include, Path

route_patterns = [
    Include(
        namespace="myapp.accounts.urls",
        pattern="my_urls",
    )
]
