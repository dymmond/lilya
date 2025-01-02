from lilya.apps import Lilya
from lilya.routing import Include
from lilya.staticfiles import StaticFiles


app = Lilya(routes=[
    Include('/static', app=StaticFiles(directory='static/overwrites', fall_through=True), name="static1"),
    Include('/static', app=StaticFiles(directory=['static', 'static/fallback'], fall_through=True), name="static2"),
    Include('/static', app=StaticFiles(directory="static/errors"), name="static_errors"),
])
