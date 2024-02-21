from lilya.apps import Lilya
from lilya.routing import Host, Router

internal = Router()
api = Router()
external = Router()

routes = [Host("api.example.com", api, name="api")]
app = Lilya(routes=routes)

app.host("www.example.com", internal, name="intenal_site")
external_host = Host("external.example.com", external)

app.router.routes.append(external)
