from lilya.routing import Include

route_patterns = [
    Include(
        namespace="myapp.accounts.urls",
        pattern="my_urls",
    ),
]
