from __future__ import annotations

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedreferrer import TrustedReferrerMiddleware
from lilya.routing import Include

routes = [
    Include("/api", routes=[], middleware=[
        # allow non-referred requests (non-user) or as referrer example.com, external.example.com
        DefineMiddleware(TrustedReferrerMiddleware, block_untrusted_referrers=True, allowed_referrers=["", "example.com", "external.example.com"]),
        # mark referals from "external.example.com" as trusted, disable same origin logic
        # You can check now `referrer_is_trusted` in the scope.
        DefineMiddleware(TrustedReferrerMiddleware, allow_same_origin=False, allowed_referrers=["external.example.com"])
    ]),
    Include("/settings", routes=[], middleware=[
        # only allow access from example. Exclude non-webrowsers which doesn't send a referrer header
        DefineMiddleware(TrustedReferrerMiddleware, allow_same_origin=False, block_untrusted_referrers=True, allowed_referrers=["example.com"]),
    ]),
    # mark referals from "example.com" and the same origin as trusted
    # Import e.g. data for a search
    Include("/", routes=[], middleware=[
        DefineMiddleware(TrustedReferrerMiddleware, allowed_referrers=["example.com"])
    ])
]

app = Lilya(routes=routes)
