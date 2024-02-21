from lilya.apps import Lilya
from lilya.routing import Include

app = Lilya(
    routes=[
        Include(
            "/",
            app=...,
        )
    ]
)
