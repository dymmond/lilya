from lilya.apps import Lilya

app = Lilya()

app.add_websocket_route(
    path=...,
    handler=...,
    name=...,
    middleware=...,
    permissions=...,
)
