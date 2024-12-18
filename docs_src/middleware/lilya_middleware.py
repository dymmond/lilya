from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedhost import TrustedHostMiddleware

app = Lilya(
    routes=[...],
    middleware=[
        DefineMiddleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "*.example.com"],
        ),
        # you can also use import strings
        DefineMiddleware("lilya.middleware.httpsredirect.HTTPSRedirectMiddleware"),
    ],
)
