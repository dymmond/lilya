# Responses

Lilya, by design, furnishes specific response classes that serve a dual purpose. They offer
utility and are tasked with sending the appropriate ASGI messages through the `send` channel.

Lilya automatically includes the `Content-Length` and `Content-Type` headers.

## How does it work

There are a few ways of using the responses within a Lylia application.

* You can [import the appropriate](#importing-the-appropriate-class) `response` class and use it directly.
* You can [build the response](#build-the-response).
* You can [delegate to Lilya](#delegate-to-lilya).
* [Build a custom encoder](#build-a-custom-encoder) that will allow Lilya to automatically parse the response.

## Available responses

All the responses from Lilya inherit from the parent object `Response` and that same class can
also be used directly.

All the responses are considered ASGI applications, which means you can treat them as such in
your application if necessary.

**Example**

```python
from lilya.responses import PlaiText
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = PlaiText('Welcome')
    await response(scope, receive, send)
```


### Response

```python
from lilya.responses import Response
```

**Example**

```python
{!> ../docs_src/responses/response.py !}
```

##### Set cookie

Lilya provides the `set_cookie` that allows settings a cookie on a given response. All the responses
available in Lilya have access to this functionality.

```python
from lilya.responses import Response
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = Response('Welcome', media_type='text/plain')

    response.set_cookie(key=..., value=..., max_age=..., expires=...,)
    await response(scope, receive, send)
```

###### Parameters

The available parameters of the `set_cookie` are as follow:

- `key` - A string representing the cookie's key.
- `value` - A string representing the cookie's value.
- `max_age` - An integer defining the cookie's lifetime in seconds.
A negative value or 0 discards the cookie immediately. *(Optional)*
- `expires` - Either an integer indicating the seconds until the cookie expires or a datetime. *(Optional)*
- `path` - A string specifying the subset of routes to which the cookie applies. *(Optional)*
- `domain` - A string specifying the valid domain for the cookie. *(Optional)*
- `secure` - A boolean indicating that the cookie is sent to the server only if the request
uses SSL and the HTTPS protocol. *(Optional)*
- `httponly` - A boolean indicating that the cookie is inaccessible via JavaScript through Document.cookie,
the XMLHttpRequest, or Request APIs. *(Optional)*
- `samesite` - A string specifying the samesite strategy for the cookie, with valid values of `'lax'`, `'strict'`, and `'none'`.
Defaults to 'lax'. *(Optional)*

##### Delete cookie

In the same fashion as the [set cookie](#set-cookie), this function is available on every response provided by
Lilya.

```python
from lilya.responses import Response
from lilya.types import Scope, Receive, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send):
    assert scope['type'] == 'http'
    response = Response('Welcome', media_type='text/plain')

    response.delete_cookie(key=..., path=..., domain=...)
    await response(scope, receive, send)
```

###### Parameters

The available parameters of the `set_cookie` are as follow:

- `key` - A string representing the cookie's key.
- `path` - A string specifying the subset of routes to which the cookie applies. *(Optional)*
- `domain` - A string specifying the valid domain for the cookie. *(Optional)*

### HTMLResponse

Returning an `html` response.

```python
from lilya.responses import HTMLResponse
```

**Example**

```python
{!> ../docs_src/responses/html.py !}
```

### Error

Response that can be used when throwing a `500` error. Defaults to return an `html` response.

```python
from lilya.responses import Error
```

**Example**

```python
{!> ../docs_src/responses/error.py !}
```

### PlainText

Response that can be used to return `text/plain`.

```python
from lilya.responses import PlainText
```

**Example**

```python
{!> ../docs_src/responses/plain.py !}
```

### JSONResponse

Response that can be used to return `application/json`.

```python
from lilya.responses import JSONResponse
```

**Example**

```python
{!> ../docs_src/responses/json.py !}
```

### Ok

Response that can be used to return `application/json` as well. You can see this as an
alternative to `JSONResponse`.

```python
from lilya.responses import Ok
```

**Example**

```python
{!> ../docs_src/responses/ok.py !}
```

### RedirectResponse

Used for redirecting the responses.

```python
from lilya.responses import RedirectResponse
```

**Example**

```python
{!> ../docs_src/responses/redirect.py !}
```

### StreamingResponse

```python
from lilya.responses import StreamingResponse
```

**Example**

```python
{!> ../docs_src/responses/streaming.py !}
```

### FileResponse

```python
from lilya.responses import FileResponse
```

Streams a file asynchronously as the response, employing a distinct set of arguments for instantiation compared to other response types:

- `path` - The filepath to the file to stream.
- `status_code` - The Status code to return.
- `headers` - Custom headers to include, provided as a dictionary.
- `media_type` - A string specifying the media type. If unspecified, the filename or path is used to deduce the media type.
- `filename` - If specified, included in the response Content-Disposition.
- `content_disposition_type` - Included in the response Content-Disposition. Can be set to `attachment` (default) or `inline`.
- `background` - A [task](./tasks.md) instance.

**Example**

```python
{!> ../docs_src/responses/file.py !}
```

## Importing the appropriate class

This is the classic most used way of using the responses. The [available responses](#available-responses)
contains a list of available responses of Lilya but you are also free to design your own and apply them.

**Example**

```python
{!> ../docs_src/responses/json.py !}
```

## Build the Response

This is where the things get great. Lilya provides a `make_response` function that automatically
will build the response for you.

```python
from lilya.responses import make_response
```

**Example**

```python
{!> ../docs_src/responses/make.py !}
```

By default, the `make_response` returns a [JSONResponse](#jsonresponse) but that can be also
changed if the `response_class` parameter is set to something else.

So, why is this `make_response` different from the other responses? Well, here its where Lilya shines.

Lilya is pure Python, which means that it does not rely or depend on external libraries like Pydantic,
msgspec, attrs or any other **but allows you to [build a custom encoder](#build-a-custom-encoder) that
can later be used to serialise your response automatically and then passed to the `make_response`.

Check the [build a custom encoder](#build-a-custom-encoder) and [custom encoders with make_response](#custom-encoders-and-the-make_response)
for more details and how to leverage the power of Lilya.

## Delegate to Lilya

Delegating to Lilya means that if no response is specified, Lilya will go through the internal
`encoders` and will try to `jsonify` the response for you.

Let us see an example.

```python
{!> ../docs_src/responses/delegate.py !}
```

As you can see, no `response` was specified but instead a python `dict` was returned. What Lilya
internally does is to *guess* and understand the type of response parse the result into `json`
and returning a `JSONResponse` automatically,

If the type of response is not json serialisable, then a `ValueError` is raised.

Let us see some more examples.

```python
{!> ../docs_src/responses/delegate_examples.py !}
```

And the list goes on and on. Lilya by design understands almost every single datastructure of Python
by default, including `Enum`, `deque`, `dataclasses`, `PurePath`, `generators` and `tuple`.

### Default Encoders

In order to understand how to serialise a specific object into `json`, Lilya has some default
encoders that evaluates when tries to *guess* the response type.

* `DataclassEncoder` - Serialises `dataclass` objects.
* `EnumEncoder` - Serialises `Enum` objects.
* `PurePathEncoder` - Serializes `PurePath` objects.
* `PrimitiveEncoder` - Serializes python primitive types. `str, int, float and None`.
* `DictEncoder` - Serializes `dict` types.
* `StructureEncoder` - Serializes more complex data types. `list, set, frozenset, GeneratorType, tuple, deque`.

What a brand new encoder is needed and it is not natively supported by Lilya? Well, [building a custom encoder](#build-a-custom-encoder)
is extremly easy and possible.

## Build a custom encoder

As mentioned before, Lilya has [default encoders](#default-encoders) that are used to transform a response
into a `json` serialisable response.

To build a custom encoder you must use the `Encoder` class from Lilya and override the `serialize()` function
where it applies the serialisation process of the encoder type.

Then you **must register the encoder** for Lilya to use it.

When defining an encoder the `__type__` or `def is_type(self, value: Any) -> bool:`
**must be declared or overridden**.

When the `__type__` is properly declared, the default `is_type` will evaluate the object against the
type and return `True` or `False`.

This is used internally to understand the type of encoder that will be applied to a given object.

!!! warning
    If you are not able to provide the `__type__` for any reason and you just want to override the
    default evaluation process, simple override the `is_type()` and apply your custom logic there.

    E.g.: In Python 3.8, for a Pydantic `BaseModel` if passed in the `__type__`, it will throw an
    error due to Pydantic internals, so to workaround this issue, you can simply override the `is_type()`
    and apply the logic that validates the type of the object and returns a boolean.

```python
from lilya.encoders import Encoder, register_encoder
```

**Example**

Create and register an encoder that handles `msgspec.Struct` types.

```python
{!> ../docs_src/responses/encoders/example.py !}
```

Simple right? Because now the `MsgSpecEncoder` is registered, you can simply do this in your handlers
and return **directly** the `msgspec.Struct` object type.

```python
from msgspec import Struct

from lilya.routing import Path


class User(Struct):
    name: str
    email: str


def msgspec_struct():
    return User(name="lilya", url="example@lilya.dev")
```

### Design specific custom encoders

**Lilya being 100% pure python and not tight to any particular validation library** allows you to
design custom encoders that are later used by Lilya responses.

Ok, this sounds a bit confusing right? I bet it does so let us go slowly.

Imagine you want to use a particular validation library such as [Pydantic](https://pydantic.dev/),
[msgspec](https://jcristharif.com/msgspec/) or even [attrs](https://www.attrs.org/en/stable/) or something
else at your choice.

You want to make sure that if you return a pydantic model or a msgspec Struct or even a `define` attr class.

Let us see how it would look like for all of them.

**For Pydantic BaseModel**

```python
{!> ../docs_src/responses/encoders/pydantic.py !}
```

**For msgspec Struct**

```python
{!> ../docs_src/responses/encoders/example.py !}
```

**For attrs**

```python
{!> ../docs_src/responses/encoders/attrs.py !}
```

Easy and poweful, right? Yes.

Do you understand what does this mean? Means you can design **any encoder** at your choice using
also any library of your choice as well.

The flexibility of Lilya allows you to be free and for Lilya not to be tight to any particular
library.

#### Custom encoders and responses

After the [custom encoders in the examples](#build-a-custom-encoder) are created, this allows to
do something like this directly.

```python
{!> ../docs_src/responses/encoders/responses.py !}
```

#### Custom encoders and the `make_response`

Well, here its where the `make_response` helps you. The `make_response` will generate a `JSONResponse`
by default and when you return a custom encoder type, there are some limitations to it.

For example, what if you want to return with a different `status_code`? Or even attach a [task](./tasks.md)
to it?

The custom encoder **does not handle** that for you but the `make_response` does!

Let us see how it would look like now using the `make_response`.

```python
{!> ../docs_src/responses/encoders/make_response.py !}
```
