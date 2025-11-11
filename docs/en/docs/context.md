# Context

The `Context` is a beauty of an object unique to **Lilya**. The `context` is a parameter that
can be used **inside the function handlers** and provides additional information
that you might need for any particular reason.

Very similar approach to [Request](./requests.md) in terms of implementation but not the same.
In fact, a `context` contains also the request and information about the handler itself.

Importing is as simple as:

```python
from lilya.context import Context
```

## The `Context` class

You can see the `context` as the `request context` of a given handler. This also means, when
a function handler (view) is declared all the information passed to it
is automatically accessible via `context.handler` parameter.

```python
{!> ../../../docs_src/context/app.py !}
```

The `context` also provides access to the [`request`](./requests.md) object as well as the
[application settings](./settings.md) and other functions.

This means, if you want to pass a `request` and `context` you actually only need the `context`
directly as the request is already available inside but you can still pass both anyway.

**Example**

```python
from lilya.apps import Lilya
from lilya.context import Context
from lilya.routing import Path


def read_context(context: Context, id: str):
    host = context.request.client.host

    context_data = context.get_context_data()
    context.add_to_context("name", "Lilya")

    context_data = context.get_context_data()
    context_data.update({
        "host": host, "user_id": id
    })
    return context_data


app = Lilya(
    routes=[
        Path("/users/{id}", read_request)
    ]
)
```

The `context` becomes especially valuable when you need to retrieve `handler` information that is
unavailable after the handler's instantiation. For instance, it proves useful when accessing
`context.settings` to retrieve application settings, offering a versatile approach to accessing them.

## Attributes

### Handler

The function handler that is responsible for the request.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    handler = context.handler

    return Response("Ok")
```

### Request

The request being used for the scope of the handler.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    request = context.request

    return Response("Ok")
```

### User

The user allocated in the request.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    user = context.user

    return Response("Ok")
```

### User

The user allocated to the request.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    user = context.user

    return Response("Ok")
```

### Settings

The [settings](./settings.md) being used by the Lilya application.

This can be the global settings or if a `settings_module` was provided, returns that
same settings.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    settings = context.settings

    return Response("Ok")
```

### Scope

The scope of the application handler.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    scope = context.scope

    return Response("Ok")
```

### Application

The Lilya application.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    app = context.app

    return Response("Ok")
```

## Methods

The `context` provides also different functions to manipulate the object.

### get_context_data

The context of the application. This can be particularly useful when
working with templates.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    context = context.get_context_data()

    return Response("Ok")
```

### add_to_context

Adding values into the current context.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    context.add_to_context("call", "ok")

    return Response("Ok")
```

### url_path_for

Retrives the path of a specific handler.

```python
from lilya.context import Context
from lilya.responses import Response


def home(context: Context):
    url = context.url_path_for("/home")

    return Response(url)
```

## The `G` object

This object is a pretty cool one, it is what allows you to have a global request context across
the lifecycle.

Imagine the following. You have a deceorator that validates a login and wants to store arbitrary
data inside a request global context to be used later on and once the request is closed, then its
cleared.

This is where the `G` object comes to play. Imagine the `g` of Flask, same principle.

This object is globally used and on each request it will be "reset", meaning, it only lives
in the request context of the call.

```python
from lilya.apps import Lilya
from lilya.context import g
from lilya.middleware import DefineMiddleware
from lilya.middleware.global_context import GlobalContextMiddleware
from lilya.routing import Path


def populate_g():
    g.name = "Lilya"
    g.age = 25


async def show_g():
    return g.store

app = Lilya(
    routes=[Path("/show", show_g)]
)

populate_g()
```

This of course is a very simple example and probably not like how you would like to use but it
explains how to use the `g`. After every request/websocket connection, the `g` is cleared.

Imagine now you want to use it in a `decorator`.

```python
import functools

from lilya.apps import Lilya
from lilya.context import g
from lilya.middleware import DefineMiddleware
from lilya.middleware.global_context import GlobalContextMiddleware
from lilya.routing import Path


def user_check(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not hasattr(g, "user"):
            g.user = "not logged in"
        return await func(*args, **kwargs)

    return wrapper


@user_check
async def show_g():
    return g.store


app = Lilya(
    routes=[Path("/show", show_g)]
)
```

This example is closer to the reality of the use of a `g` like validating a login against anything
in your APIs.

### Populating g automatically

We can also pass a parameter `populate_context` (Middleware), `populate_global_context` (Lilya) which takes the current Connection
as parameter and is expected to return sync/asynchronously a dict with initial values for `g`.
This can be handy to automatically provide a context without an extra middleware.
You can also copy here values from a parent `g`.


### The LifespanGlobalContextMiddleware

You may want to use `g` also for lifespans. Here we have `LifespanGlobalContextMiddleware`.
It doesn't has a `populate_context` parameter and ignores `populate_global_context` (Lilya).
Liya comes by default with this middleware activated. So you are also able to use `g` in lifespans.

## The `RequestContext` object

This is a very useful object that acts a lazy loader of the request object without the need of
explicitly declaring it inside an handler.

!!! Danger
    When using the `request_context` object, you **must** install the [RequestContextMiddleware](./middleware.md#requestcontextmiddleware)
    or an `ImproperlyConfigured` exception is raised.

```python
from lilya.apps import Lilya
from lilya.context import request_context
from lilya.middleware import DefineMiddleware
from lilya.middleware.request_context import RequestContextMiddleware
from lilya.routing import Path


async def show_request_context():
    return {"url": str(request_context.url)}


app = Lilya(routes=[
        Path('/show', show_request_context)
    ],
    middleware=[DefineMiddleware(RequestContextMiddleware)],
)
```

## The `Session` object

This is also a very useful object that can be used in a lazy load mode across the request lifecycle. If you are familiar
with the flask `session`, this one acts in the same fashion.

!!! Danger
    When using the `session` object, you **must** install the [SessionMiddleware](./middleware.md#sessioncontextmiddleware)
    and the [SessionContextMiddleware](./middleware.md#sessioncontextmiddleware) in this specific order as the order matters or an `ImproperlyConfigured` exception is raised.

```python
{!> ../../../docs_src/context/basic_session.py !}
```

### Multiplexing

For bigger applications you might want to multiplex a session into multiple session contexts. You can do that by providing `sub_path`.

```python
{!> ../../../docs_src/context/multiplexed_session.py !}
```
