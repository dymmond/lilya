# Middleware

Lilya includes several middleware classes unique to the application but also allowing some other ways of designing
them by using `protocols`.

## Lilya middleware

The Lilya middleware is the classic already available way of declaring the middleware within an **Lilya**
application.

```python
{!> ../../../docs_src/middleware/lilya_middleware.py !}
```

## Lilya protocols

Lilya protocols are not too different from the [Lilya middleware](#lilya-middleware). In fact,
the name itself happens only because of the use of the
<a href="https://peps.python.org/pep-0544/" target="_blank">python protocols</a>
which forces a certain structure to happen.

When designing a middleware, you can inherit and subclass the **MiddlewareProtocol** provided by Lilya.

```python
{!> ../../../docs_src/middleware/protocols.py !}
```

### MiddlewareProtocol

For those coming from a more enforced typed language like Java or C#, a protocol is the python equivalent to an
interface.

The `MiddlewareProtocol` is simply an interface to build middlewares for **Lilya** by enforcing the implementation of
the `__init__` and the `async def __call__`.

Enforcing this protocol also aligns with writing a [Pure ASGI Middleware](#pure-asgi-middleware).

### Quick sample

```python
{!> ../../../docs_src/middleware/sample.py !}
```

## Middleware and the application

Creating this type of middlewares will make sure the protocols are followed and therefore reducing development errors
by removing common mistakes.

To add middlewares to the application is very simple.

=== "Application level"

    ```python
    {!> ../../../docs_src/middleware/adding_middleware.py !}
    ```

=== "Any other level"

    ```python
    {!> ../../../docs_src/middleware/any_other_level.py !}
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


## BaseAuthMiddleware & AuthenticationMiddleware

These are a very special middlewares and and helps with any authentication middleware that can be used within
an **Lilya** application but like everything else, you can design your own.

`BaseAuthMiddleware` is also an abstract class that simply enforces the implementation of the `authenticate` method and
assigning the result object into a `tuple[AuthCredentials | None, UserInterface | None]` or None and make it available on every request.

`AuthenticationMiddleware` is an implementation using backends and most people will prefer it.
See [Authentication](./authentication.md) for more details.

### Example of a JWT middleware class

```python title='/src/middleware/jwt.py'
{!> ../../../docs_src/middleware/auth_middleware_example.py !}
```

1. Import the `BaseAuthMiddleware` from `lilya.middleware.authentication`.
2. Implement the `authenticate` and return `tuple[AuthCredentials, UserInterface]` (AuthResult) or None or raise.

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

    from lilya.conf.global_settings import Settings
    from lilya.middleware import DefineMiddleware


    @dataclass
    class AppSettings(Settings):

        @property
        def middleware(self) -> List[DefineMiddleware]:
            return [
                # you can also use absolute import strings
                DefineMiddleware("project.middleware.jwt.JWTAuthMiddleware")
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
{!> ../../../docs_src/middleware/settings.py !}
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
* `TrustedHostMiddleware` - Restricts the hosts used for connecting if a given `allowed_hosts` is populated. Optionally just provide a `host_is_trusted` parameter in the scope.
* `TrustedReferrerMiddleware` - Handles with the CORS if a given `allowed_hosts` is populated.
* `GZipMiddleware` - Compression middleware `gzip`.
* `HTTPSRedirectMiddleware` - Middleware that handles HTTPS redirects for your application. Very useful to be used
for production or production like environments.
* `SessionMiddleware` - Middleware that handles the sessions.
* `SessionFixingMiddleware` - Middleware that fixes sessions to client ips.
* `WSGIMiddleware` - Allows to connect WSGI applications and run them inside Lilya. A [great example](./wsgi.md)
how to use it is available.
* `XFrameOptionsMiddleware` - Middleware that handles specifically against clickjacking.
* `SecurityMiddleware` - Provides several security enhancements to the request/response cycle and adds security headers to the response.
* `ClientIPMiddleware` - Provides facilities to retrieve the client ip. This can be useful for ratelimits.
* `GlobalContextMiddleware` - Allows the use of the `[g](./context.md#the-g-object)` across request contexts. For Lilya by default active.
* `LifespanGlobalContextMiddleware` - Allows the use of the `[g](./context.md#the-g-object)` in lifespan requests. For Lilya by default active.
* `RequestContextMiddleware` - Adds a `request_context` object context without the need to use handlers.
* `AuthenticationMiddleware` & `BaseAuthMiddleware` - See [above](#baseauthmiddleware--authenticationmiddleware).
* `SessionContextMiddleware`- Adds a `session` object context to be accessed in the handlers or request context in general.

### CSRFMiddleware

The default parameters used by the CSRFMiddleware implementation are restrictive by default and Lilya allows some
ways of using this middleware depending of the taste.

```python
{!> ../../../docs_src/middleware/available/csrf.py !}
```

### CORSMiddleware

The default parameters used by the CORSMiddleware implementation are restrictive by default and Lilya allows some
ways of using this middleware depending of the taste.

```python
{!> ../../../docs_src/middleware/available/cors.py !}
```

### SessionMiddleware

Adds signed cookie-based HTTP sessions. Session information is readable but not modifiable.

```python
{!> ../../../docs_src/middleware/available/sessions.py !}
```

By default session data is restricted to json.dumps serializable data.
If you want more speed or more datatypes you can pass a different serializer/deserializer, e.g. orjson:

```python
{!> ../../../docs_src/middleware/available/sessions_orjson.py !}
```

Note however when using json not all datatypes are idempotent.
You might want to use dataclasses, msgstruct, RDF or (not recommended because of security issues: pickle).

You can also automatically initialize sessions with data via the `populate_session` parameter.
It isn't repopulated until the next request after the session is cleared. So you can change data as you wish.

```python
{!> ../../../docs_src/middleware/available/sessions_populate_session.py !}
```

### HTTPSRedirectMiddleware

Enforces that all incoming requests must either be https or wss. Any http os ws will be redirected to
the secure schemes instead.

```python
{!> ../../../docs_src/middleware/available/https.py !}
```

### TrustedHostMiddleware

Enforces all requests to have a correct set `Host` header in order to protect against host header attacks.

More details in [TrustedHostMiddleware](./middleware/trustedhost.md)

### TrustedReferrerMiddleware

Check `host` and `referer` header to check if the referral was allowed and set the variable in the scope.

More details in [TrustedReferrerMiddleware](./middleware/trustedreferrer.md)


### GZipMiddleware

It handles GZip responses for any request that includes "gzip" in the Accept-Encoding header.

```python
{!> ../../../docs_src/middleware/available/gzip.py !}
```

### WSGIMiddleware

A middleware class in charge of converting a WSGI application into an ASGI one. There are some more examples
in the [WSGI Frameworks](./wsgi.md) section.

```python
{!> ../../../docs_src/middleware/available/wsgi.py !}
```

The `WSGIMiddleware` also allows to pass the `app` as a string `<dotted>.<path>` and this can make it
easier for code organisation.

Let us assume the previous example of the `flask` app was inside `myapp/asgi_or_wsgi/apps`. Like this:

```python
{!> ../../../docs_src/middleware/available/wsgi_str.py !}
```

To call it inside the middleware is as simple as:

```python
{!> ../../../docs_src/middleware/available/wsgi_import.py !}
```

### XFrameOptionsMiddleware

The clickjacking middleware that provides easy-to-use protection against clickjacking.
This type of attack occurs when a malicious site tricks a user into clicking on a concealed element of another site which they have loaded in a hidden frame or iframe.

This middleware reads the value `x_frame_options` from the [settings](./settings.md) and defaults to `DENY`.

This also adds the `X-Frame-Options` to the response headers.

```python
{!> ../../../docs_src/middleware/available/clickjacking.py !}
```

### SecurityMiddleware

Provides several security enhancements to the request/response cycle and adds security headers to the response.

```python
{!> ../../../docs_src/middleware/available/security.py !}
```

### ClientIPMiddleware & ClientIPScopeOnlyMiddleware

Parses the client ip and add it in the request scope as `real-clientip` entry.
It also adds the standard `x-real-ip` to the request headers.

```python
{!> ../../../docs_src/middleware/available/clientip.py !}
```

There are two special "ip"s: "*" and "unix".

The first one is a match all and implies all proxies are trustworthy,
the second one applies when a unix socket is used or no client ip address was found.

If you don't want an injected header use the `ClientIPScopeOnlyMiddleware`:

```python
{!> ../../../docs_src/middleware/available/clientip_scope_only.py !}
```

!!! Note
    If you don't want to use the middleware you can use: `get_ip` from `lilya.clientip` directly.

!!! Note
    It is currently not possible to simulate a client ip address in lilyas TestClient. So you may want to use the Forwarded header and trust "unix" for tests.


### SessionFixingMiddleware

Sometimes you want to tie a session to an ip. If the IP changes, the session is resetted and optionally a notification is sent.
This way we can prevent session stealing / session replay attacks.
It requires the `SessionMiddleware` and the `ClientIPMiddleware` (or the `ClientIPScopeOnlyMiddleware`).

```python
{!> ../../../docs_src/middleware/available/session_fixing.py !}
```

!!! Note
    Drawback is a periodically logout if you have a client with a changing ip address.
    E.g. working remotely from trains or using tor.

!!! Tip
    You can use the `notify_fn` parameter to update the `new_session` with data from the `old_session` when appropiate.


### RequestContextMiddleware

Lazy loads a request object without explicitly add it into the handlers.

```python
{!> ../../../docs_src/middleware/available/request_context.py !}
```

### SessionContextMiddleware

Lazy loads a session object without explicitly go through the `request.session` object. This can be accessed within
the request context of any handler.

The `SessionContextMiddleware` **depends** on the [SessionMiddleware](#sessionmiddleware) to **also be installed** and the
**order matters**.

```python
{!> ../../../docs_src/middleware/available/session_context_middleware.py !}
```

You can multiplex a single session by providing `sub_path`:

```python
{!> ../../../docs_src/middleware/available/session_context_middleware_sub_path.py !}
```

!!! Note
    This doesn't affect `request.session` or `scope["session"]`. Here you have still the original session object.

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

## Important points

1. Lilya supports [Lilya middleware](#lilya-middleware) ([MiddlewareProtocol](#lilya-protocols)).
2. A `MiddlewareProtocol` is simply an interface that enforces `__init__` and `async __call__` to be implemented.
3. `app` is required parameter from any class inheriting from the `MiddlewareProtocol`.
4. [Pure ASGI Middleware](#pure-asgi-middleware) is encouraged and the `MiddlewareProtocol` enforces that.
1. Middleware classes can be added to any [layer of the application](#quick-note)
2. All authentication middlewares must inherit from the BaseAuthMiddleware.
3. You can load the **application middleware** in different ways.
