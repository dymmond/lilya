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
{!> ../docs_src/context/app.py !}
```

The `context` also provides access to the [`request`](./requests.md) object as well as the
[application settings](./application/settings.md) and other functions.

This means, if you want to pass a `request` and `context` you actually only need the `context`
directly as the request is already available inside but you can still pass both anyway.

**Example**

```python
from esmerald import Context, Lilya, Gateway, get


@get("/users/{id}")
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
        Gateway(handler=read_request)
    ]
)
```

The `context` can be particularly useful if you want to access `handler` information that is not
available after the handler is instantiated, for example and can be very useful if you also want
to access the `context.settings` where the application settings are available, another versatile way
of accessing them.
