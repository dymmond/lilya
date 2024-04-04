# Routing

Lilya has a simple but highly effective routing system capable of handling from simple routes to the most
complex.

Using  an enterprise application as example, the routing system surely will not be something simple with
20 or 40 direct routes, maybe it will have 200 or 300 routes where those are split by responsabilities,
components and packages and imported also inside complex design systems.
Lilya handles with those cases without any kind of issues at all.

## Router

The Router is the main object that links the whole Lilya to the [Path](#path),
[WebSocketPath](#websocketpath) and [Include](#include).

## Router class

The router class is composed by many attributes that are by default populated within the application but Lilya
also allows to add extra [custom routers](#custom-router) as well but another way is to add a
[ChildLilya](#child-lilya-application) application.

```python
{!> ../docs_src/routing/router/router_class.py!}
```

The main `Router` class is instantiated within the `Lilya` application with the given routes and the application
starts.

### Parameters

When creating a [Path](#path) or [WebSocketPath](#websocketpath) function handler, you have two ways
of getting the path parameters.

* Lilya auto discovers and injects them for you.
* You get them from the [request](./requests.md) object.

#### Auto discovering the parameters

This is probably the easiest and simplest way.

```python
{!> ../docs_src/routing/handlers/patch.py !}
```

The `customer_id` declared in the `path` was also declared in the function handler allowing Lilya
to inject the **values found by order from the path parameters** for you.

#### From the `request` path parameters.

```python
{!> ../docs_src/routing/handlers/request.py !}
```

The `customer_id` declared in the `path` was obtained by accessing the `request` object.

## Custom Router

Let's assume there are specific **customer** submodules inside a `customers` dedicated file.
There are two way of separating the routes within the application, using [Include](#include),
a [ChildLilya](#child-lilya-application) or by creating another router. Let's focus on the latter.

```python title="/application/apps/routers/customers.py"
{!> ../docs_src/routing/router/customers.py!}
```

Above you create the `/application/apps/routers/customers.py` with all the information you need. It does not need
to be in one file, you can have a entirely seperate package just to manage the customer, it is up to you.

Now you need to add the new custom router into the main application.

```python title="/application/app.py"
{!> ../docs_src/routing/router/app.py!}
```

This simple and your router is added to the main **Lilya** application.

## ChildLilya Application

What is this? We call it `ChildLilya` but in fact is simply Lilya but under a different name mostly for
visualisation purposes and for the sake of organisation.

!!! Check
    Using `ChildLilya` or `Lilya` is exactly the same thing, it is only if you prefer to create a
    `sub application` and you prefer to use a different class instead of `Lilya` to make it more organised.

### How does it work

Let's use the same example used in the [custom routers](#custom-router) with the customers specific routes and rules.

```python title="/application/apps/routers/customers.py"
{!> ../docs_src/routing/router/childlilya/customers.py!}
```

Since the `ChildLilya` is a representation of a [Lilya](./applications.md) class, we can pass
the otherwise limited parameters in the [custom router](#custom-router) and all the parameters available to
[Lilya](./applications.md).

You can add as many `ChildLilya` as you desire, there are no limits.

**Now in the main application**:

```python title="/application/app.py"
{!> ../docs_src/routing/router/childlilya/app.py!}
```

**Adding nested applications**

```python title="/application/app.py"
{!> ../docs_src/routing/router/childlilya/nested.py!}
```

The example above, it is showing that you could even add the same application within nested includes and for each
include you can add specific unique [permissions](./permissions.md) and [middlewares](./middleware.md) which are available on each
instance of the `Include`. The options are endeless.

!!! Note
    In terms of organisation, `ChildLilya` has a clean approach to the isolation of responsabilities and allow
    treating every individual module separately and simply adding it in to the main application
    in the form of [Include](#include).

!!! Tip
    Treat the `ChildLilya` as an independent `Lilya` instance.

!!! Check
    When adding a `ChildLilya` or `Lilya` application, don't forget to add the unique path to the base
    `Include`, this way you can assure the routes are found properly.

## Utils

The `Router` object has some available functionalities that can be useful.

### add_route()

```python
{!> ../docs_src/routing/router/add_route.py!}
```

#### Parameters

* **path** - The path for the child lilya.
* **name** - Name of the route.
* **handler** - The function handler.
* **methods** - The available http verbs for the path.
* **include_in_schema** - If route should be added to the OpenAPI Schema
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md)  to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.

### add_websocket_route()

```python
{!> ../docs_src/routing/router/add_websocket_route.py!}
```

#### Parameters

* **path** - The path for the child lilya.
* **name** - Name of the route.
* **handler** - The function handler.
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md)  to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.

### add_child_lilya()

```python
{!> ../docs_src/routing/router/add_child_lilya.py!}
```

#### Parameters

* **path** - The path for the child lilya.
* **child** - The [ChildLilya](#child-lilya-application) instance.
* **name** - Name of the route.
* **handler** - The function handler.
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md)  to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.
* **include_in_schema** - Boolean if this ChildLilya should be included in the schema.
* **deprecated** - Boolean if this ChildLilya should be marked as deprecated.

## Path

The object that connects and builds the application urls or paths. It maps the function handler
with the application routing system

#### Parameters

* **path** - The path for the child lilya.
* **name** - Name of the route.
* **handler** - The function handler.
* **methods** - The available http verbs for the path.
* **include_in_schema** - If route should be added to the OpenAPI Schema
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md) to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.
* **deprecated** - Boolean if this ChildLilya should be marked as deprecated.

=== "In a nutshell"

    ```python
    {!> ../docs_src/routing/routes/gateway_nutshell.py!}
    ```

## WebSocketPath

Same principle as [Path](#path) with one particularity. The websockets are `async`.

#### Parameters

* **path** - The path for the child lilya.
* **name** - Name of the route.
* **handler** - The function handler.
* **include_in_schema** - If route should be added to the OpenAPI Schema
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md) to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.
* **deprecated** - Boolean if this ChildLilya should be marked as deprecated.

=== "In a nutshell"

    ```python
    {!> ../docs_src/routing/routes/websocket_nutshell.py!}
    ```

## Include

Includes are unique to Lilya, powerful and with more control and allows:

1. Scalability without issues.
2. Clean routing design.
3. Separation of concerns.
4. Separation of routes.
5. Reduction of the level of imports needed through files.
6. Less human lead bugs.

!!! Warning
    Includes **DO NOT** take path parameters. E.g.: `Include('/{name:path}, routes=[...])`.

### Include and application

This is a very special object that allows the import of any routes from anywhere in the application.
`Include` accepts the import via `namespace` or via `routes` list but not both.

When using a `namespace`, the `Include` will look for the default `route_patterns` list in the imported
namespace (object) unless a different `pattern` is specified.

The patten only works if the imports are done via `namespace` and not via `routes` object.

#### Parameters

* **path** - The path for the child lilya.
* **app** - An application can be anything that is treated as an ASGI application. The `app` can be
an ASGI related app of a string `<dotted>.<module>` location of the app.
* **routes** - A global `list` of lilya routes. Those routes may vary and those can
be `Path`, `WebSocketPath` or even another `Include`.
* **namespace** - A string with a qualified namespace from where the URLs should be loaded.
* **pattern** - A string `pattern` information from where the urls shall be read from.
* **name** - Name of the Include.
* **permissions** - A list of [permissions](./permissions.md) to serve the application incoming
requests (HTTP and Websockets).
* **middleware** - A list of [middleware](./middleware.md) to run for every request.
* **exception handlers** - A dictionary of [exception types](./exceptions.md) (or custom exceptions) and the handler
functions on an application top level. Exception handler callables should be of the form of
`handler(request, exc) -> response` and may be be either standard functions, or async functions.
* **include_in_schema** - If route should be added to the OpenAPI Schema
* **deprecated** - Boolean if this `Include` should be marked as deprecated.

=== "Importing using namespace"

    ```python title='myapp/urls.py'
    {!> ../docs_src/routing/routes/include/with_namespace.py!}
    ```

=== "Importing using routes list"

    ```python title='src/myapp/urls.py'
    {!> ../docs_src/routing/routes/include/routes_list.py!}
    ```

=== "Import the app via string"

    This is an alternative of loading the app via `string` import instead
    of passing the object directly.

    ```python title='src/myapp/urls.py'
    {!> ../docs_src/routing/routes/include/app_str.py!}
    ```

#### Using a different pattern

```python title="src/myapp/accounts/controllers.py"
{!> ../docs_src/routing/routes/include/views.py!}
```

```python title="src/myapp/accounts/urls.py"
{!> ../docs_src/routing/routes/include/different_pattern.py!}
```

=== "Importing using namespace"

    ```python title='src/myapp/urls.py'
    {!> ../docs_src/routing/routes/include/namespace.py!}
    ```

#### Include and application instance

The `Include` can be very helpful mostly when the goal is to avoid a lot of imports and massive list
of objects to be passed into one single object. This can be particularly useful to make a clean start
Lilya object as well.

**Example**:

```python title='src/urls.py'
{!> ../docs_src/routing/routes/include/app/urls.py!}
```

```python title='src/app.py'
{!> ../docs_src/routing/routes/include/app/app.py!}
```

## Nested Routes

When complexity increses and the level of routes increases as well, `Include` allows nested routes in a clean fashion.

=== "Simple Nested"

    ```python hl_lines="9"
    {!> ../docs_src/routing/routes/include/nested/simple.py!}
    ```

=== "Complex Nested Routes"

    ```python hl_lines="10-41"
    {!> ../docs_src/routing/routes/include/nested/complex.py!}
    ```

`Include` supports as many nested routes with different paths and Includes as you
desire to have. Once the application starts, the routes are assembled and it will immediatly available.

Nested routes also allows all the functionalities on each level, from middleware and permissions.

### Application routes

!!! warning
    Be very careful when using the `Include` directly in the Lilya(routes[]), importing without a `path` may incur
    in some routes not being properly mapped.

**Only applied to the application routes**:

If you decide to do this:

```python
{!> ../docs_src/routing/routes/careful/example1.py!}
```

## Host

If you aim to utilize distinct routes for the same path contingent on the Host header, Lilya provides a solution.

It's important to note that the port is disregarded from the Host header during matching. For instance,
`Host(host='example.com:8081', ...)` will be processed regardless of whether the Host header contains a port
different from 8081 (e.g., `example.com:8083`, `example.org`). Therefore, if the port is essential for `path_for`
purposes, you can explicitly specify it.

There are multiple approaches to establish host-based routes for your application.

```python
{!> ../docs_src/routing/routes/host.py !}
```

URL lookups can encompass host parameters, similar to how path parameters are included.

```python
{!> ../docs_src/routing/routes/host_encompass.py !}
```

## Routes priority

The [application routes](#application-routes) in simple terms are simply prioritised. The incoming paths are matched agains each [Path](#path),
[WebSocketPath](#websocketpath) and [Include](#include) in order.

In cases where more than one, let's say Path could match an incoming path, you should ensure that more specifc
routes are listed before general cases.

Example:

```python
{!> ../docs_src/routing/routes/routes_priority.py !}
```

## Path parameters

Paths can use templating style for path components. The path params are only applied to [Path](#path) and
[WebSocketPath](#websocketpath) and **not applied** to [Include](#include).

**Remember that there are [two ways of handling with the path parameters](#auto-discovering-the-parameters)**.

```python
async def customer(customer_id: Union[int, str]) -> None:
    ...


async def floating_point(number: float) -> None:
    ...

Path("/customers/{customer_id}/example", handler=customer)
Path("/floating/{number:float}", handler=customer)
```

By default this will capture characters up to the end of the path of the next `/` and it will become `/customers/{customer_id}/example`.

**Transformers** can be used to modify what is being captured and the type of what is being captured.
Lilya provides some default path transformers.

* `str` returns a string, and is the default.
* `int` returns a Python integer.
* `float` returns a Python float.
* `uuid` returns a Python `uuid.UUID` instance.
* `path` returns the rest of the path, including any additional `/` characters.
* `datetime` returns the datetime.

As per standard, the transformers are used by prefixing them with a colon:

```python
Path('/customers/{customer_id:int}', handler=customer)
Path('/floating-point/{number:float}', handler=floating_point)
Path('/uploaded/{rest_of_path:path}', handler=uploaded)
```

### Custom transformers

If a need for a different transformer that is not defined or available, you can also create your own.

```python
{!> ../docs_src/routing/routes/transformer_example.py !}
```

With the custom transformer created you can now use it.

```python
Path('/network/{address:ipaddress}', handler=network)
```

## Middleware, exception Handlers and permissions

### Examples

The following examples are applied to [Path](#path), [WebSocketPath](#websocketpath)
and [Include](#include).

We will be using Path for it can be replaced by any of the above as it is common among them.

#### Middleware

As specified before, the [middleware](./middleware.md) of a Path are read from top down,
from the parent to the very handler and the same is applied to [exception handlers](./exceptions.md),
and [permissions](./permissions.md).

```python
{!> ../docs_src/routing/routes/middleware.py !}
```

The above example illustrates the various levels where a middleware can be implemented and because it follows an
parent order, the order is:

1. Default application built-in middleware.
2. `RequestLoggingMiddlewareProtocol`.
3. `ExampleMiddleware`.

**More than one middleware can be added to each list.**

#### Exception Handlers

```python
{!> ../docs_src/routing/routes/exception_handlers.py !}
```

The above example illustrates the various levels where the exception handlers can be implemented and follows a
parent order where the order is:

1. Default application built-in exception handlers.
3. `InternalServerError : http_internal_server_error_handler`.
4. `NotAuthorized: http_not_authorized_handler`.

More than one exception handler can be added to each mapping.

#### Permissions

Permissions are a must in **every** application. More on [permissions](./permissions.md) and how
to use them.

```python
{!> ../docs_src/permissions/any_other_level.py !}
```

**More than one permission can be added to each list.**

## Reverse Path lookups

Frequently, there is a need to generate the URL for a specific route, especially in scenarios where a redirect
response is required.

```python
{!> ../docs_src/routing/routes/lookup.py !}
```

The lookups also allow path parameters.

```python
{!> ../docs_src/routing/routes/lookup_path.py !}
```

If an `Include` includes a name, subsequent submounts should employ a `{prefix}:{name}` format for reverse Path lookups.

### Using the `reverse`

This is an alternative for the reverse path lookup. It can be particularly useful if you want to
reverse a path in testing or in isolation.


#### Parameters

* **name** - The name given to the path.
* **app** - An ASGI application containing the routes. Useful for reversing paths on specific applications and/or testing. *(Optional)*.
* **path_params** - A dictionary like object containing the parameters that should be passed in a given path. *(Optional)*.

Using the `reverse`, if no `app` parameter is specified, it will automatically default to the application or application router,
which under normal circunstances, besides `testing`, it is the expected behaviour.

```python
{!> ../docs_src/routing/routes/reverse.py !}
```

The reverse also allow path parameters.

```python
{!> ../docs_src/routing/routes/reverse_path.py !}
```
