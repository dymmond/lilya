from lilya.routing import Include

# There is an app in the location `myapp.asgi_or_wsgi.apps.child_lilya`

route_patterns = [
    Include(
        "/child",
        app="myapp.asgi_or_wsgi.apps.child_lilya",
    ),
]
