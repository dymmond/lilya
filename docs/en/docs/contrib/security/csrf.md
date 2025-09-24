# CSRF Protection

[CSRFMiddleware](../../middleware.md#csrfmiddleware) protects your application against Cross‑Site Request Forgery (CSRF)
using the **double‑submit cookie** pattern. It is secure by default and now supports **traditional HTML forms** without JavaScript,
in addition to the header‑based approach commonly used by XHR/fetch.

## Quick Start

```python
from __future__ import annotations

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware

routes = [...]

# Minimal setup
app = Lilya(
    routes=routes,
    middleware=[
        DefineMiddleware(
            CSRFMiddleware,
            secret="your-long-unique-secret",
            # Optional (see below):
            # form_field_name="csrf_token",
            # max_body_size=2 * 1024 * 1024,
            # httponly=False,  # set False if templates must read cookie value
            # secure=True,     # enable in production (HTTPS)
            # samesite="lax",
        )
    ],
)
```

!!! Tip "Using settings"
    You can also configure the middleware via your settings `LILYA_SETTINGS_MODULE`. See the [Settings](../../settings.md) section.

## How it Works

On **safe methods** (by default `GET`, `HEAD`):

* If the CSRF cookie (default name: `csrftoken`) is **missing**, the middleware **injects** it into the response.

On **unsafe methods** (`POST`, `PUT`, `PATCH`, `DELETE`):

1.  The middleware first checks the **header**: `X‑CSRFToken`.
2.  If the header is missing and the body is a **form** (`application/x-www-form-urlencoded` or `multipart/form-data`), it will:
    * **Buffer** the request body,
    * Extract the CSRF token from a hidden field (default name: `csrf_token`),
    * **Replay** the exact same body to the downstream app, so handlers can still call `await request.form()` or `await request.body()` without change.
3.  It then validates that the submitted token (header or form) **matches the cookie**.

Tokens are signed and compared in constant time. The middleware delegates token generation and verification to the shared utilities in `lilya.contrib.security.csrf`.

## Configuration

### Parameters

```python
CSRFMiddleware(
    app: ASGIApp,
    secret: str,
    *,
    cookie_name: str | None = "csrftoken",
    header_name: str | None = "X-CSRFToken",
    cookie_path: str | None = "/",
    safe_methods: set[str] | None = {"GET", "HEAD"},
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] = "lax",
    domain: str | None = None,

    # New
    form_field_name: str = "csrf_token",
    max_body_size: int = 2 * 1024 * 1024,
)
```

* **secret** *(required)*: Server key to HMAC‑sign tokens.
* **cookiename**: Name of the CSRF cookie (default: `csrftoken`).
* **headername**: Header for XHR/fetch token (default: `X‑CSRFToken`).
* **safemethods**: Methods that skip CSRF validation (default: `{"GET", "HEAD"}`).
* **secure / httponly / samesite / domain / cookiepath**: Cookie attributes.
    * Set **`secure=True`** in production.
    * Set **`httponly=False`** if your templates need to **read** the cookie (for hidden inputs).
* **formfieldname** *(new)*: Hidden input field name to read token from when header is absent (default: `csrf_token`).
* **maxbodysize** *(new)*: Safety cap for buffering request bodies during form fallback (default: 2 MiB).

## Real‑World Usage

### 1. XHR / fetch & SPA/HTMX

```javascript
async function postData(url, data) {
  // Grab the CSRF cookie (csrftoken=...)
  const csrf = document.cookie
    .split("; ")
    .find((c) => c.startsWith("csrftoken="))
    ?.split("=")[1];

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf, // <-- header-based token
    },
    credentials: "same-origin",
    body: JSON.stringify(data),
  });
  return res.json();
}
```

!!! info "Observation"
    This path is ideal for SPAs, HTMX, and progressive enhancement—no need to read the cookie in templates.

### 2. File Upload Forms (multipart)

Add a hidden field with the token. The middleware understands `multipart/form-data`:

### 3. Custom Hidden Field Name

Prefer a different name (e.g., `csrfmiddlewaretoken`)? Configure it:

```python
DefineMiddleware(
    CSRFMiddleware,
    secret="your-long-unique-secret",
    form_field_name="csrfmiddlewaretoken",
    httponly=False,
)
```

## CSRF Utilities (`lilya.contrib.security.csrf`)

To keep things DRY, the middleware uses shared helpers. You can also use them directly in views, tests, or custom flows.

```python
from lilya.contrib.security.csrf import (
    generate_csrf_token,
    decode_csrf_token,
    tokens_match,
    build_csrf_cookie,
    ensure_csrf_cookie,
    get_or_set_csrf_token,
)
```

### Common Helpers

* `generate_csrf_token(secret: str) -> str` - Returns a new signed CSRF token.

* `decode_csrf_token(secret: str, token: str) -> str | None` - Validates and returns the token's secret part or `None`.

* `tokens_match(secret: str, a: str | None, b: str | None) -> bool` - Constant‑time check: tokens are valid and represent the same underlying value.

* `build_csrf_cookie(...) -> Cookie` - Builds a `Cookie` instance prefilled with a fresh token.

* `ensure_csrf_cookie(response, secret, **cookie_opts) -> str` - Adds a CSRF cookie to the response if you need one **immediately**. Returns the token value.

* `get_or_set_csrf_token(request, response, secret, **cookie_opts) -> str` - Returns the existing CSRF cookie value if present, otherwise
sets a new one and returns it—perfect for first‑time GETs that render forms.

## Advanced Topics

### Body Replay (Form Fallback)

When the header is absent and the request body is a form, the middleware buffers the body to extract the hidden field and then **replays** the same body to your app. This guarantees downstream code can still read the body normally:

```python
async def handler(request):
    form = await request.form()  # works even if middleware parsed earlier
    ...
```

### Large Bodies

Parsing is capped by `max_body_size`. If exceeded, the middleware **skips** fallback parsing and the request will fail CSRF unless a header token is provided.

```python
DefineMiddleware(
    CSRFMiddleware,
    secret="...",
    max_body_size=64 * 1024,  # 64 KiB for small forms
)
```

## Security Notes & Best Practices

* **Always enable `secure=True`** in production so the cookie is only sent over HTTPS.
* **`HttpOnly`**:
    - Keep `httponly=True` if you use the **header** path exclusively (you don't need to read the cookie in templates).
    - Set `httponly=False` if you **render the token** into a hidden form field from the cookie.
* **`SameSite`**: `lax` is a sane default for most apps; adjust for your cross‑site embed needs.
* **Scope**: Use `cookie_path="/"` unless you want tokens limited to a sub‑path.
* **Rotate secret** carefully—revoking all tokens may temporarily fail outstanding form submissions.

## Troubleshooting

**403: CSRF token verification failed**

* Missing cookie? Ensure a prior `GET` set it, or call `get_or_set_csrf_token` in your GET handler.
* Header missing? If you're using XHR/fetch, send `X‑CSRFToken`.
* Using classic forms? Ensure you render a hidden input named `csrf_token` (or your custom `form_field_name`) with the **exact cookie value**.
* Large body? Increase `max_body_size` or provide the token via header.
* Different domains/subdomains? Check cookie `domain` and `samesite` settings.

## A quick example "how to"

Let us go through a quick example how to practically use this. We will be using Jinja for it as well
as the [TemplateController](../../templates.md#templatecontroller) to make it easier to show.

Feel free to use whatever you want.

**The HTML**

```html title="login.html"
<!doctype html>
<html>
    <body>
    <h1>Login</h1>
    <form action="." method="POST">
        <label>Username <input type="text" name="username" required></label><br>
        <label>Password <input type="password" name="password" required></label><br>
        <!-- Hidden CSRF field -->
        <input type="hidden" name="csrf_token" value="{{ token }}">
        <button type="submit">Login</button>
    </form>
    </body>
</html>
```

**The handler or Controller**

Now its time for the handler.

```python
from typing import Any

from lilya.requests import Request
from lilya.responses import HTML, Ok
from lilya.contrib.security.csrf import get_or_set_csrf_token
from lilya.templating.controllers import TemplateController

class LoginController(TemplateController):
    template_name = "login.html"
    csrf_enabled = True

    async def get(self, request: Request) -> HTML:
        return await self.render_template(request)

    async def post(self, request: Request) -> HTML:
        # Get the form
        form = await request.form()

        # Do things and return
        ...

    # Return your HTML response
```

With `csrf_enabled=True`, Lilya will inject the `csrf_token` automatically for you in the variable `csrf_token`.
You can override this value by overriding the `csrf_token_form_name` to whatever value you desire.

**The application**

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.middleware import DefineMiddleware
from lilya.middleware.csrf import CSRFMiddleware


app = Lilya(
    routes=[
        Path("/login", LoginController, name="login"),
    ],
    middleware=[
        DefineMiddleware(
            CSRFMiddleware,
            secret=CSRF_SECRET,
            secure=False,  # True in production (HTTPS)
            samesite="lax",
            httponly=True,
        )
    ],
)
```

Because we embed the server‑generated token directly, we can keep the cookie **HttpOnly** (more secure), since the browser JS doesn't need to read it.

!!! Tip "Observation"
    The reason why we use TemplateController its because its cleaner and more organised for this
    example but you are free to use functions if you are more comfortable with.

## What the middleware does vs. what you must do

**Automatically done by `CSRFMiddleware`:**

* Sets the CSRF cookie on safe methods if missing.
* On unsafe methods, validates:
    * `X‑CSRFToken` header **or**
    * hidden form field (fallback) in `application/x-www-form-urlencoded` or `multipart/form-data`.
* Rejects invalid/missing tokens with `403 PermissionDenied`.

**You still need to:**

* **Include** the token in submissions:
    * Hidden field (classic forms), **or**
    * Header (XHR/fetch/HTMX).
* On first page render, **ensure a token exists** and embed it:
    * Use `get_or_set_csrf_token(request, response=, secret=...)` from `lilya.contrib.security.csrf` to set the cookie *and* get the token value.
* Choose cookie flags:
    * **Recommended** for SSR: `httponly=True` (since you embed token directly in HTML).
    * For JS‑read cookie patterns, keep `httponly=False` (less secure; only if you need to read the cookie in JS).

## Notes

* **Validation is automatic** (the middleware will reject/allow unsafe requests).
* **Supplying the token is *not* automatic**—your HTML must include the CSRF token either:
    * As a **hidden form field** (for classic forms), or
    * As an **HTTP header** (for XHR/fetch/HTMX).
