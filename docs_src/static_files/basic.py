from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static'), name="static"),
])
