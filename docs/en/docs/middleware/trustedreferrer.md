# TrustedReferrerMiddleware

Check if the sent referrer is `same-origin` or matches trusted referrer hosts.
In contrast to the TrustedHostMiddleware by default nothing is enforced and only a flag (`referrer_is_trusted`) is set in the scope.
You can change this by providing `block_untrusted_referrers=True`.
When used for an API it is recommended to add `""` to `allowed_referrers`. This evaluates requests
without a set referrer header as valid.

## When to use it

This middleware is useful when you want lightweight origin trust checks for browser-originating traffic.

Typical cases:

* admin or dashboard routes;
* form-heavy internal tools;
* APIs with browser clients where referer policy matters.

## Parameters

* `allowed_referrers`: iterable of allowed host patterns (supports wildcard like `*.example.com`).
* `allow_same_origin`: trusts requests where referer host matches request host.
* `block_untrusted_referrers`: when `True`, untrusted referrers return `400`.

### Minimal setup

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.trustedreferrer import TrustedReferrerMiddleware

app = Lilya(
    middleware=[
        DefineMiddleware(
            TrustedReferrerMiddleware,
            allowed_referrers=["example.com", "*.example.com", ""],
            allow_same_origin=True,
            block_untrusted_referrers=False,
        )
    ]
)
```

```python
{!> ../../../docs_src/middleware/available/trusted_referrers_simple.py !}
```

Let's go fancy and block also invalid referred request or requests not originating from web browsers

```python
{!> ../../../docs_src/middleware/available/trusted_referrers.py !}
```

## See also

* [Middleware](../middleware.md) for ordering and composition.
* [TrustedHostMiddleware](./trustedhost.md) for host header validation.
* [CSRF Protection](../contrib/security/csrf.md) for anti-CSRF token strategy.
