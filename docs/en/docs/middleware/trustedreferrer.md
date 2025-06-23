# TrustedReferrerMiddleware

Check if the sent referrer is `same-origin` or matches trusted referrer hosts.
In contrast to the TrustedHostMiddleware by default nothing is enforced and only a flag (`referrer_is_trusted`) is set in the scope.
You can change this by providing `block_untrusted_referrers=True`.
When used for an API it is recommended to add `""` to `allowed_referrers`. This evaluates requests
without a set referrer header as valid.

```python
{!> ../../../docs_src/middleware/available/trusted_referrers_simple.py !}
```

Let's go fancy and block also invalid referred request or requests not originating from web browsers

```python
{!> ../../../docs_src/middleware/available/trusted_referrers.py !}
```
