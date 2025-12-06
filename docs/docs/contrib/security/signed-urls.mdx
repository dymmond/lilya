# Signed URL Generator & Signed Redirect

Lilya provides a built-in system for generating and verifying **signed URLs** with expiration, as well as a `SignedRedirect`
response class that issues redirects to signed URLs.

```python
from lilya.contrib.security.signed_urls import SignedURLGenerator, SignedRedirect
```

## Overview

The **Signed URL system** in Lilya allows developers to generate **tamper-proof, time-limited URLs** for secure
access to resources such as:

* File downloads
* Private media links
* Authenticated redirect flows
* One-time verification links
* Password reset or magic login URLs

Every signed URL contains a cryptographic **HMAC signature** and an **expiration timestamp**, ensuring that:

1. The URL **cannot be modified** without detection.
2. The URL **automatically expires** after the given time window.

This is essential for protecting endpoints that must be temporarily accessible, e.g., links sent to external clients
or users who shouldn't have permanent access.

## How It Works

At the core lies the `SignedURLGenerator`:

```python
from lilya.contrib.security.signed_urls import SignedURLGenerator

signer = SignedURLGenerator(secret_key="supersecret")

signed = signer.sign("https://example.com/resource", expires_in=300)
print(signed)
# -> https://example.com/resource?expires=1739311820&sig=naK3F_q3s4LzZQnBiRAaXq...

signer.verify(signed)  # True (before expiry)
```

The signature is derived from:

```
HMAC(secret_key, f"{path}?expires={timestamp}&<other_params>")
```

This ensures:

* **Integrity** — Any modification to the path or query invalidates the signature.
* **Expiration** — If the timestamp is older than `now()`, the URL fails verification.
* **Algorithm flexibility** — You can use any hash algorithm supported by `hashlib` (`sha256`, `sha512`, etc.).

## Class Reference

### `SignedURLGenerator`

#### Initialization

```python
SignedURLGenerator(secret_key: str, algorithm: str = "sha256")
```

| Parameter    | Type  | Description                                                                                          |
| ------------ | ----- | ---------------------------------------------------------------------------------------------------- |
| `secret_key` | `str` | Secret used to sign URLs. Must be kept private and consistent across signing and verifying services. |
| `algorithm`  | `str` | Hash algorithm to use for the HMAC. Default is `"sha256"`.                                           |

#### Signing URLs

```python
sign(url: str, expires_in: int = 3600) -> str
```

| Parameter    | Type  | Description                                                |
| ------------ | ----- | ---------------------------------------------------------- |
| `url`        | `str` | The URL to be signed.                                      |
| `expires_in` | `int` | Time (in seconds) before the URL expires. Default: 1 hour. |

Returns a fully signed URL with `?expires=<ts>&sig=<signature>` appended.

**Example:**

```python
signer = SignedURLGenerator("key123")
signed = signer.sign("https://myapp.com/downloads/video.mp4", expires_in=600)
print(signed)
# -> https://myapp.com/downloads/video.mp4?expires=1739312400&sig=abcd1234xyz
```

#### Verifying URLs

```python
verify(signed_url: str) -> bool
```

| Parameter    | Type  | Description              |
| ------------ | ----- | ------------------------ |
| `signed_url` | `str` | A previously signed URL. |

Returns `True` if:

* The signature matches, and
* The current time < `expires`

Otherwise returns `False`.

## `SignedRedirect`

A subclass of `RedirectResponse` that **automatically signs** its target URL using a `SignedURLGenerator`.

#### **Usage**

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.security.signed_urls import SignedRedirect, SignedURLGenerator

signer = SignedURLGenerator("supersecret")

async def go():
    return SignedRedirect("https://example.com/secure", signer, expires_in=300)

app = Lilya(routes=[Path("/redirect", go)])
```

This sends a redirect response with a signed `Location` header:

```
Location: https://example.com/secure?expires=1739311920&sig=abc...
```

## Dependency Injection Integration

Signed URL signing can be **injected** through Lilya's dependency system, ideal when your app shares a global
signing key or uses multiple scopes.

### Example 1 — Global scope (one signer across app)

```python
from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.contrib.security.signed_urls import SignedURLGenerator, SignedRedirect
from lilya.routing import Path

signer = SignedURLGenerator(secret_key="global-key")

async def redirect_endpoint(signer=Provides()):
    return SignedRedirect("https://example.com/profile", signer, expires_in=120)

app = Lilya(
    dependencies={"signer": Provide(lambda: signer, scope="GLOBAL")},
    routes=[Path("/redir", redirect_endpoint)],
)
```

✅ The same signer instance is reused for every request, great for global app secrets.

### Example 2 — App scope (isolated per sub-app)

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.security.signed_urls import SignedURLGenerator
from lilya.dependencies import Provide, Provides
created = []

def factory():
    signer = SignedURLGenerator(secret_key="per-app-key")
    created.append(signer)
    return signer

async def endpoint(signer=Provides()):
    return {"signed": signer.sign("https://example.com/app", expires_in=30)}

sub1 = Lilya(dependencies={"signer": Provide(factory, scope="APP")}, routes=[Path("/a", endpoint)])
sub2 = Lilya(dependencies={"signer": Provide(factory, scope="APP")}, routes=[Path("/b", endpoint)])
```

* ✅ Each app mount gets its own instance.
* ✅ Global state isolation, useful for multi-tenant or per-customer setups.

### Example 3 — Mixed scopes

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.security.signed_urls import SignedURLGenerator
from lilya.dependencies import Provide, Provides
from lilya.enums import Scope

def global_factory():
    return SignedURLGenerator("global-secret")

def request_factory():
    return SignedURLGenerator("request-secret")

async def endpoint(global_signer=Provides(), req_signer=Provides()):
    u1 = global_signer.sign("https://example.com/a", expires_in=30)
    u2 = req_signer.sign("https://example.com/b", expires_in=30)
    return {"valid1": global_signer.verify(u1), "valid2": req_signer.verify(u2)}

app = Lilya(
    dependencies={
        "global_signer": Provide(global_factory, scope=Scope.GLOBAL),
        "req_signer": Provide(request_factory, scope=Scope.REQUEST),
    },
    routes=[Path("/multi", endpoint)],
)
```

* ✅ `GLOBAL` — one instance reused
* ✅ `REQUEST` — new signer each request
* ✅ Best pattern when mixing user-specific and global secrets.

## When to Use Signed URLs

| Use Case                    | Description                                                                      |
| --------------------------- | -------------------------------------------------------------------------------- |
| **Temporary Downloads**     | Grant time-limited access to S3, GCS, or CDN resources.                          |
| **Private Redirects**       | Safely redirect users to external destinations after verifying a token or login. |
| **Magic Login Links**       | Send one-time authentication URLs via email.                                     |
| **User Verification Links** | Sign verification links to prevent tampering.                                    |
| **Expiring Invitations**    | Create share links that expire after a time window.                              |

## What Signed URLs Are Not

* They **do not encrypt** the URL, they only ensure integrity and validity.
* They **should not be used as authentication tokens**; instead, use them to gate access for already authenticated
or limited scope actions.

## Example: Secure File Download Endpoint

```python
from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.contrib.security.signed_urls import SignedURLGenerator
from lilya.responses import FileResponse
from lilya.routing import Path

signer = SignedURLGenerator("media-secret")

async def generate_link(signer=Provides()):
    signed = signer.sign("https://cdn.example.com/private/video.mp4", expires_in=300)
    return {"download_url": signed}

async def serve_file(request):
    url = str(request.url)
    if not signer.verify(url):
        return {"error": "Link expired or invalid"}, 403
    return FileResponse("/data/private/video.mp4")

app = Lilya(
    dependencies={"signer": Provide(lambda: signer, scope="GLOBAL")},
    routes=[
        Path("/link", generate_link),
        Path("/media/video.mp4", serve_file),
    ],
)
```

## Key Takeaways

| Concept                 | Explanation                                                |
| ----------------------- | ---------------------------------------------------------- |
| **Integrity**           | HMAC ensures URLs cannot be tampered with.                 |
| **Expiry**              | `expires` timestamp automatically invalidates old links.   |
| **Dependency-Friendly** | Works seamlessly with Lilya's DI system.                   |
| **Flexible Scoping**    | Supports `REQUEST`, `APP`, and `GLOBAL` scopes.            |
| **Framework Agnostic**  | `SignedURLGenerator` can be used standalone without Lilya. |

## Summary

The **Signed URL and Redirect** system is one of Lilya's most practical security primitives — small but powerful.
It balances simplicity and robustness, ensuring your links remain secure, temporary, and verifiable, both in internal redirects and in user-facing workflows.
