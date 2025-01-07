from lilya.apps import Lilya
from lilya.routing import Path, Include

app = Lilya(
    routes=[
        Include(
            "/",
            namespace="src.urls",
            name="performance",
            redirect_slashes=False
        ),
        Include(
            "/",
            app=...,
            name="app",
        ),
    ]
)
