from lilya.apps import Lilya

app = Lilya()

app.add_route(
    path=...,
    methods=...,
    name=...,
    middleware=...,
    permissions=...,
    include_in_schema=...,
)
