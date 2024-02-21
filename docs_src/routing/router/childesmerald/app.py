from apps.routers.customers import router as customers_router
from lilya.apps import Lilya
from lilya.routing import Include

app = Lilya(
    routes=[
        Include("/customers", app=customers_router),
    ]
)
