# TrustedHostMiddleware

Enforces all requests to have a correct set `Host` header in order to protect against host header attacks.
Injects `host_is_trusted` flag into the scope.

```python
{!> ../../../docs_src/middleware/available/trusted_hosts.py !}
```

When an automatic blocking is not wanted, pass `block_untrusted_host=False`.
This way only a flag named `host_is_trusted` in the scope is set.
An use-case is to unlock some special features only for internal host names.

```python
{!> ../../../docs_src/middleware/available/trusted_hosts_stacked.py !}
```
