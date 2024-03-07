# Middleware

Lilya includes several middleware classes unique to the application but also allowing some other ways of designing
them by using `protocols`.

## Lilya middleware

The Lilya middleware is the classic already available way of declaring the middleware within an **Lilya**
application.

```python
{!> ../docs_src/middleware/lilya_middleware.py !}
```

## Lilya protocols

Lilya protocols are not too different from the [Lilya middleware](#lilya-middleware). In fact,
the name itself happens only because of the use of the
<a href="https://peps.python.org/pep-0544/" target="_blank">python protocols</a>
which forces a certain structure to happen.

When designing a middleware, you can inherit and subclass the **MiddlewareProtocol** provided by Lilya.

```python
{!> ../docs_src/middleware/protocols.py !}
```

### MiddlewareProtocol

For those coming from a more enforced typed language like Java or C#, a protocol is the python equivalent to an
interface.

The `MiddlewareProtocol` is simply an interface to build middlewares for **Lilya** by enforcing the implementation of
the `__init__` and the `async def __call__`.

Enforcing this protocol also aligns with writing a [Pure ASGI Middleware](#pure-asgi-middleware).

### Quick sample

```python
{!> ../docs_src/middleware/sample.py !}
```

## Middleware and the application

Creating this type of middlewares will make sure the protocols are followed and therefore reducing development errors
by removing common mistakes.

To add middlewares to the application is very simple.

=== "Application level"

    ```python
    {!> ../docs_src/middleware/adding_middleware.py !}
    ```

=== "Any other level"

    ```python
    {!> ../docs_src/middleware/any_other_level.py !}
    ```

### Quick note

!!! Info
    The middleware is not limited to `Lilya`, `ChildLilya`, `Include` and `Path`.
    We simply choose `Path` as it looks simpler to read and understand.

## Pure ASGI Middleware

Lilya follows the [ASGI spec](https://asgi.readthedocs.io/en/latest/).
This capability allows for the implementation of ASGI middleware using the
ASGI interface directly. This involves creating a chain of ASGI applications that call into the next one.
Notably, this approach mirrors the implementation of middleware classes shipped with Lilya.

**Example of the most common approach**

```python
from lilya.types import ASGIApp, Scope, Receive, Send


class MyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.app(scope, receive, send)
```

When implementing a Pure ASGI middleware, it is like implementing an ASGI application, the first
parameter **should always be an app** and the `__call__` should **always return the app**.

## BaseAuthMiddleware

This is a very special middleware and helps with any authentication middleware that can be used within
an **Lilya** application but like everything else, you can design your own.

`BaseAuthMiddleware` is also a protocol that simply enforces the implementation of the `authenticate` method and
assigning the result object into a `AuthResult` and make it available on every request.

### Example of a JWT middleware class

```python title='/src/middleware/jwt.py'
{!> ../docs_src/middleware/auth_middleware_example.py !}
```

1. Import the `BaseAuthMiddleware` and `AuthResult` from `lilya.middleware.authentication`.
2. Implement the `authenticate` and assign the `user` result to the `AuthResult`.

#### Import the middleware into a Lilya application

=== "From the application instance"

    ```python
    from lilya import Lilya
    from lilya.middleware import DefineMiddleware
    from .middleware.jwt import JWTAuthMiddleware


    app = Lilya(routes=[...], middleware=[DefineMiddleware(JWTAuthMiddleware)])
    ```

=== "From the settings"

    ```python
    from dataclasses import dataclass
    from typing import List

    from lilya.conf import Settings
    from lilya.middleware import DefineMiddleware
    from .middleware.jwt import JWTAuthMiddleware


    @dataclass
    class AppSettings(Settings):

        @property
        def middleware(self) -> List[DefineMiddleware]:
            return [
                DefineMiddleware(JWTAuthMiddleware)
            ]

    # load the settings via LILYA_SETTINGS_MODULE=src.configs.live.AppSettings
    app = Lilya(routes=[...])
    ```

!!! Tip
    To know more about loading the settings and the available properties, have a look at the
    [settings](./settings.md) docs.

## Middleware and the settings

One of the advantages of Lilya is leveraging the settings to make the codebase tidy, clean and easy to maintain.
As mentioned in the [settings](./settings.md) document, the middleware is one of the properties available
to use to start a Lilya application.

```python title='src/configs/live.py'
{!> ../docs_src/middleware/settings.py !}
```

**Start the application with the new settings**


```shell
LILYA_SETTINGS_MODULE=configs.live.AppSettings uvicorn src:app

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [28720]
INFO:     Started server process [28722]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

!!! attention
    If `LILYA_SETTINGS_MODULE` is not specified as the module to be loaded, **Lilya** will load the default settings
    but your middleware will not be initialized.

### Important

If you need to specify parameters in your middleware then you will need to wrap it in a
`lilya.middleware.DefineMiddleware` object to do it so. See `GZipMiddleware` [example](#middleware-and-the-settings).

## Available middlewares

* `CSRFMiddleware` - Handles with the CSRF.
* `CORSMiddleware` - Handles with the CORS.
* `TrustedHostMiddleware` - Handles with the CORS if a given `allowed_hosts` is populated.
* `GZipMiddleware` - Compression middleware `gzip`.
* `HTTPSRedirectMiddleware` - Middleware that handles HTTPS redirects for your application. Very useful to be used
for production or production like environments.
* `SessionMiddleware` - Middleware that handles the sessions.
* `WSGIMiddleware` - Allows to connect WSGI applications and run them inside Lilya. A [great example](./wsgi.md)
how to use it is available.

### CSRFMiddleware

The default parameters used by the CSRFMiddleware implementation are restrictive by default and Lilya allows some
ways of using this middleware depending of the taste.

```python
{!> ../docs_src/middleware/available/csrf.py !}
```

### CORSMiddleware

The default parameters used by the CORSMiddleware implementation are restrictive by default and Lilya allows some
ways of using this middleware depending of the taste.

```python
{!> ../docs_src/middleware/available/cors.py !}
```

### SessionMiddleware

Adds signed cookie-based HTTP sessions. Session information is readable but not modifiable.

```python
{!> ../docs_src/middleware/available/sessions.py !}
```

### HTTPSRedirectMiddleware

Enforces that all incoming requests must either be https or wss. Any http os ws will be redirected to
the secure schemes instead.

```python
{!> ../docs_src/middleware/available/https.py !}
```

### TrustedHostMiddleware

Enforces all requests to have a correct set `Host` header in order to protect against heost header attacks.

```python
{!> ../docs_src/middleware/available/trusted_hosts.py !}
```

### GZipMiddleware

It handles GZip responses for any request that includes "gzip" in the Accept-Encoding header.

```python
{!> ../docs_src/middleware/available/gzip.py !}
```

### WSGIMiddleware

A middleware class in charge of converting a WSGI application into an ASGI one. There are some more examples
in the [WSGI Frameworks](./wsgi.md) section.

```python
{!> ../docs_src/middleware/available/wsgi.py !}
```

The `WSGIMiddleware` also allows to pass the `app` as a string `<dotted>.<path>` and this can make it
easier for code organisation.

Let us assume the previous example of the `flask` app was inside `myapp/asgi_or_wsgi/apps`. Like this:

```python
{!> ../docs_src/middleware/available/wsgi_str.py !}
```

To call it inside the middleware is as simple as;

```python
{!> ../docs_src/middleware/available/wsgi_import.py !}
```

### Other middlewares

You can build your own middlewares as explained above but also reuse middlewares directly for any other ASGI application if you wish.
If the middlewares follow the [pure asgi](#pure-asgi-middleware) then the middlewares are 100% compatible.

#### <a href="https://github.com/abersheeran/asgi-ratelimit">RateLimitMiddleware</a>

A ASGI Middleware to rate limit and highly customizable.

#### <a href="https://github.com/snok/asgi-correlation-id">CorrelationIdMiddleware</a>

A middleware class for reading/generating request IDs and attaching them to application logs.

!!! Tip
    For Lilya apps, just substitute FastAPI with Lilya in the examples given or implement
    in the way Lilya shows in this document.

#### <a href="https://github.com/steinnes/timing-asgi">TimingMiddleware</a>

ASGI middleware to record and emit timing metrics (to something like statsd).
This integration works using [EsmeraldTimming](https://github.com/dymmond/esmerald-timing).


## Important points

1. Lilya supports [Lilya middleware](#lilya-middleware) ([MiddlewareProtocol](#lilya-protocols)).
2. A `MiddlewareProtocol` is simply an interface that enforces `__init__` and `async __call__` to be implemented.
3. `app` is required parameter from any class inheriting from the `MiddlewareProtocol`.
4. [Pure ASGI Middleware](#pure-asgi-middleware) is encouraged and the `MiddlewareProtocol` enforces that.
1. Middleware classes can be added to any [layer of the application](#quick-note)
2. All authentication middlewares must inherit from the BaseAuthMiddleware.
3. You can load the **application middleware** in different ways.
