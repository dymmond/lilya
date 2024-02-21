from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.httpsredirect import HTTPSRedirectMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware

app = Lilya(
    routes=[...],
    middleware=[
        DefineMiddleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "*.example.com"],
        ),
        DefineMiddleware(HTTPSRedirectMiddleware),
    ],
)
