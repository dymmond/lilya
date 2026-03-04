# Applications

Lilya brings a class called `Lilya` which wraps all the functionality of the application.

```python
from lilya.apps import Lilya
```

Before going deeper, the conceptual model is in:

* [Component Interactions](./concepts/component-interactions.md)
* [Layering and Precedence](./concepts/layering-and-precedence.md)

There are many ways of creating a Lilya application but:

=== "In a nutshell"

```python
{!> ../../../docs_src/applications/nutshell.py !}
```

=== "With Include"

```python
{!> ../../../docs_src/applications/with_include.py!}
```

## Testing using curl

```shell
$ curl -X GET http://localhost:8000/user/lilya
```

## Create an instance of an application

Creating an application instance can be done in different ways and with a great plus of using the
[settings](./settings.md) for a cleaner approach.

**Parameters**:

* **debug** - Boolean indicating if a debug tracebacks should be returns on errors. Basically, debug mode,
very useful for development.
* **settings_module** - A [settings](./settings.md) instance or class definition from where the settings
values will be read.
* **routes** - A list of routes to serve incoming HTTP and WebSocket requests.
A list of [Path](./routing.md#path), [WebSocketPath](./routing.md#websocketpath), [Include](./routing.md#include) and
[Host](./routing.md#host).
requests (HTTP and Websockets).
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md) to run for every request. The middlewares can be subclasses of the [MiddlewareProtocol](./middleware.md#middlewareprotocol).
* **exception_handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.
* **on_shutdown** - A list of callables to run on application shutdown. Shutdown handler callables do not take any
arguments, and may be be either standard functions, or async functions.
* **on_startup** - A list of callables to run on application startup. Startup handler callables do not take any
arguments, and may be be either standard functions, or async functions.
* **lifespan** - The lifespan context function is a newer style that replaces on_startup / on_shutdown handlers.
Use one or the other, not both.
* **include_in_schema** - Boolean flag to indicate if should be schema included or not. This can be useful
if you are deprecating a whole [Included](./routing.md#include) Lilya application in favour of a new one. The flag
should indicate that all the paths should be considered deprecated.
* **redirect_slashes** - Flag to enable/disable redirect slashes for the handlers. It is enabled by default.

## Decorating routes directly in the app

Lilya can also register routes using decorators directly on the application instance.

```python
from lilya.apps import Lilya

app = Lilya()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.route("/items", methods=["GET", "POST"])
async def items():
    return {"items": []}
```

This style is useful when you prefer route declaration close to handler definitions.

For advanced route composition (namespaces, nested include trees, host routing), keep using [routing](./routing.md).

## Runtime route registration

Besides the constructor `routes=[...]`, the app can register routes dynamically:

* `app.add_route(...)`
* `app.add_websocket_route(...)`
* `app.include(...)`
* `app.host(...)`
* `app.add_child_lilya(...)`
* `app.add_asgi_app(...)`

This can be useful for plugin-like systems or dynamically assembled applications.

## Dependency overrides (testing and controlled swaps)

Application-level dependency overrides are available at runtime:

* `app.override_dependency(key, dependency)`
* `app.reset_dependency_overrides()`

This is the recommended way to replace integrations (mail, database adapters, external clients) in tests without rewriting routes.

## Introspection graph

Every app instance exposes `app.graph`, which gives a complete graph representation of routes, includes, middleware, permissions and links between them.

This is very useful for architecture audits and debugging large route trees.

Read more in [Introspection](./introspection.md) and [Architecture Overview](./architecture.md).

## Application settings

Settings are another way of controlling the parameters passed to the
Lilya object when instantiating. Check out the [settings](./settings.md) for
more details and how to use it to power up your application.

To access the application settings there are different ways:

=== "Within the application request"

```python hl_lines="6"
{!> ../../../docs_src/applications/settings/within_app_request.py!}
```

=== "From the global settings"

```python hl_lines="1 6"
{!> ../../../docs_src/applications/settings/global_settings.py!}
```

## State and application instance

You can store arbitraty extra state on the application instance using the `state` attribute.

Example:

```python hl_lines="6"
{!> ../../../docs_src/applications/app_state.py !}
```

## Accessing the application instance

The application instance is **always** available via `request` or via `context`.

**Example**

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.context import Context
from lilya.routing import Path


# For request
def home_request(request: Request):
    app = request.app
    return {"message": "Welcome home"}


# For context
def home_context(context: Context):
    app = context.app
    return {"message": "Welcome home"}


app = Lilya(routes=[
        Path("/request", home_request),
        Path("/context", home_context),
    ]
)
```
