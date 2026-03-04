# Troubleshooting & FAQ

This page focuses on common issues seen when developing and deploying Lilya applications.

## Quick checklist

Before diving into specific errors, quickly check:

* Are you using the correct app import path (`module:app`)?
* Are your route paths starting with `/`?
* Is your `LILYA_SETTINGS_MODULE` import path valid?
* If using forms, did you install `python-multipart`?
* If using optional features (CLI, OpenAPI, etc.), did you install the right extras?

## Route returns 404 but I expected a match

Most common causes:

* Route path does not start with `/`.
* Route is mounted under an `Include` prefix you forgot.
* You expected path params on `Include` (not supported).
* Your path has a trailing slash mismatch and `redirect_slashes=False`.

Also verify route priority if multiple routes can match.

## I get `Paths must start with '/'`

`Path` and `WebSocketPath` must start with `/`.

Correct:

```python
Path("/users", handler=...)
```

Incorrect:

```python
Path("users", handler=...)
```

## I get `Either 'app=...', or 'routes=...', or 'namespace=...' must be specified`

This comes from `Include(...)`.

At least one of these must be provided:

* `app=...`
* `routes=[...]`
* `namespace="..."`

## WebSocket fails with connection state/runtime errors

If you receive errors like:

* `WebSocket is not connected. Need to call "accept" first.`

It usually means you tried to send/receive text/json/bytes before `await websocket.accept()`.

Always accept first:

```python
async def ws(websocket):
    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(data)
```

## Form parsing fails

If parsing form or multipart data fails early, ensure `python-multipart` is installed.

Lilya requires it for:

* `await request.form()`
* multipart file uploads

## `Stream consumed` when reading body

`request.stream()` consumes the body as chunks.

After consuming stream chunks, calling `request.body()`, `request.json()`, or `request.form()` is not valid for the same request body flow.

Choose one approach per request:

* `stream()` for chunk processing
* `body()`/`json()`/`form()` for buffered parsing

## Static files return 404 unexpectedly

Check these first:

* `directory` exists and is readable.
* Requested file path is really under the configured directory.
* If you expect directory behavior, set `html=True`.
* If you chain multiple `StaticFiles`, use `fall_through=True` for non-final layers.

## Runtime error when adding middleware/permissions dynamically

After startup, middleware and permissions are considered locked for safety.

Typical errors:

* `Middlewares cannot be added once the application has started.`
* `Permissions cannot be added once the application has started.`

Register middleware/permissions during app setup, not after serving requests.

## Reverse lookup fails (`NoMatchFound`)

Check:

* Route has a `name`.
* All required path params were provided.
* Nested includes use namespaced names (`prefix:name`).

## Why does caching seem local in multi-worker deployments?

`InMemoryCache` is process-local. In multi-worker setups, each worker has its own cache memory.

Use a shared backend (for example Redis) when you need cache consistency across workers.

## Settings do not look applied

Remember settings precedence:

1. Parameters passed directly to `Lilya(...)`
2. `settings_module` passed to app instance
3. `LILYA_SETTINGS_MODULE`
4. Lilya defaults

If a value looks ignored, check if it is being overridden at a higher precedence level.

## Still blocked?

When reporting an issue, include:

* Lilya version
* Python version
* ASGI server and version
* minimal reproducible route/app
* full traceback

That usually reduces turnaround time significantly.

## See also

* [Architecture Overview](./architecture.md) for route and middleware flow.
* [Routing](./routing.md) for matching and include composition.
* [Dependencies](./dependencies.md) for scope and override behavior.
* [Exceptions](./exceptions.md) for handler precedence and exception types.
