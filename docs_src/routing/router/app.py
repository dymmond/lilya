from lilya.app import Lilya
from lilya.routing import Include

app = Lilya(
    routes=[
        Include(
            "/",
            app=...,
        )
    ]
)
