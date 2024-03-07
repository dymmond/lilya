from lilya.apps import Lilya
from lilya.middleware.wsgi import WSGIMiddleware
from lilya.routing import Include

# Add the flask app into Lilya to be served by Lilya.
routes = [
    Include(
        "/external",
        app=WSGIMiddleware("myapp.asgi_or_wsgi.apps.flask"),
    ),
]

app = Lilya(routes=routes)
