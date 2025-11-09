# Controllers

Lilya embraces both functional and object-oriented programming (OOP) methodologies.
Within the Lilya framework, the OOP paradigm is referred to as a *controller*, a nomenclature inspired by other notable technologies.

The `Controller` serves as the orchestrator for handling standard HTTP requests and managing WebSocket sessions.

Internally, the `Controller` and `WebSocketController` implement the same response wrappers as the
[Path](./routing.md#path) and [WebSocketPath](./routing.md#websocketpath) making sure that remains
as one source of truth and that also means that the [auto discovery](./routing.md#auto-discovering-the-parameters) of
the parameters also works here.

## The `Controller` class

This object also serves as ASGI application, which means that embraces the internal implementation
of the `__call__` and dispatches the requests.

This is also responsible for implementing the HTTP dispatching of the requests, only.

```python
{!> ../../../docs_src/controllers/controller.py!}
```

When employing a Lilya application instance for routing management, you have the option to dispatch to a `Controller` class.

!!! warning
    It's crucial to dispatch directly to the class, not to an instance of the class.

Here's an example for clarification:

```python
{!> ../../../docs_src/controllers/dispatch.py !}
```

In this scenario, the `ASGIApp` class is dispatched, not an instance of it.

`Controller` classes, when encountering request methods that do not map to a corresponding handler,
will automatically respond with `405 Method Not Allowed` responses.

## The `WebSocketController` class

The `WebSocketController` class serves as an ASGI application, encapsulating the functionality of a `WebSocket` instance.

The ASGI connection scope is accessible on the endpoint instance through `.scope` and features an attribute called `encoding`.
This attribute, which may be optionally set, is utilized to validate the expected WebSocket data in the `on_receive` method.

The available encoding types are:

- `'json'`
- `'bytes'`
- `'text'`

There are three methods that can be overridden to handle specific ASGI WebSocket message types:

1. `async def on_connect(websocket, **kwargs)`
2. `async def on_receive(websocket, data)`
3. `async def on_disconnect(websocket, close_code)`

```python
{!> ../../../docs_src/controllers/websocketcontroller.py !}
```

The `WebSocketController` is also compatible with the Lilya application class.

```python
{!> ../../../docs_src/controllers/wdispatch.py !}
```

## Using `with_init`

Sometimes you may need to pass parameters to your controller's `__init__` method,
for example dependencies or configuration values.
Normally Lilya expects controllers to be passed as **classes**, not instances, so `MyController()` would break routing.

To solve this, you can use the `with_init()` factory method available on both `Controller` and `WebSocketController`.

This factory returns a lightweight wrapper class that Lilya can safely instantiate without arguments,
while internally constructing the real controller per request using your provided `__init__` parameters.

### Example (HTTP)

```python
{!> ../../../docs_src/controllers/with_init_http.py !}
```

### Example (WebSocket)

```python
{!> ../../../docs_src/controllers/with_init_ws.py !}
```

### How it works internally

`with_init()` creates a small singleton wrapper that Lilya can call without arguments. This wrapper:

1. Captures your constructor arguments when you call `with_init(...)`.
2. Creates a real controller instance on each request using those arguments.
3. Delegates the ASGI call or await to that real controller.

This mechanism allows controllers to be fully dynamic while keeping Lilya's routing system clean and consistent.
