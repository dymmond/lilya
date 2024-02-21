from lilya.apps import Lilya
from lilya.routing import Include

app = Lilya(
    routes=[
        Include(
            "/",
            namespace="src.urls",
            name="root",
        ),
        Include(
            "/accounts",
            namespace="accounts.v1.urls",
            name="accounts",
        ),
    ]
)
