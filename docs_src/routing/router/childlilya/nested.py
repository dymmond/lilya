from apps.routers.clients import router as clients_router
from apps.routers.customers import router as customers_router
from apps.routers.restrict import router as restrict_router

from lilya.apps import Lilya
from lilya.routing import Include

app = Lilya(
    routes=[
        Include("/customers", app=customers_router),
        Include(
            "/api/v1",
            routes=[
                Include("/clients", clients_router),
                Include("/restrict", routes=[Include("/access", restrict_router)]),
            ],
        ),
    ]
)
