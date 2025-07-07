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
{!> ../../../docs_src/responses/response.py !}
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
{!> ../../../docs_src/responses/html.py !}
```

### Error

Response that can be used when throwing a `500` error. Defaults to return an `html` response.

```python
from lilya.responses import Error
```

**Example**

```python
{!> ../../../docs_src/responses/error.py !}
```

### PlainText

Response that can be used to return `text/plain`.

```python
from lilya.responses import PlainText
```

**Example**

```python
{!> ../../../docs_src/responses/plain.py !}
```

### JSONResponse

Response that can be used to return `application/json`.

```python
from lilya.responses import JSONResponse
```

**Example**

```python
{!> ../../../docs_src/responses/json.py !}
```

### Ok

Response that can be used to return `application/json` as well. You can see this as an
alternative to `JSONResponse`.

```python
from lilya.responses import Ok
```

**Example**

```python
{!> ../../../docs_src/responses/ok.py !}
```

### RedirectResponse

Used for redirecting the responses.

```python
from lilya.responses import RedirectResponse
```

**Example**

```python
{!> ../../../docs_src/responses/redirect.py !}
```

### StreamingResponse

```python
from lilya.responses import StreamingResponse
```

**Example**

```python
{!> ../../../docs_src/responses/streaming.py !}
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
- `allow_range_requests` - Should enable support for http ranges? By default `True`. You certainly want this for continuing downloads.
- `range_multipart_boundary` - Enable multipart http ranges. Either bool or explicit string value used for the boundary. By default `False` (multipart is disabled).

**Example**

```python
{!> ../../../docs_src/responses/file.py !}
```

By default multipart ranges are disabled as it is a bit more expensive (cpu and data usage), you can enable it by setting
`range_multipart_boundary` to `True` or an explicit boundary value.

```python
{!> ../../../docs_src/responses/multi_range_file.py !}
```

By default we limit the maximum amount of requested ranges to five. For a different security approach
or different multipart parsing you can modify the `FileResponse`

```python
{!> ../../../docs_src/responses/customized_multi_range_file.py !}
```

Note however that some clients doesn't behave well (or just fallback to non-range download) if multi-range requests are answered
with a single range response and vice versa.

## Importing the appropriate class

This is the classic most used way of using the responses. The [available responses](#available-responses)
contains a list of available responses of Lilya but you are also free to design your own and apply them.

**Example**

```python
{!> ../../../docs_src/responses/json.py !}
```

## Build the Response

This is where the things get great. Lilya provides a `make_response` function that automatically
will build the response for you.

```python
from lilya.responses import make_response
```

**Example**

```python
{!> ../../../docs_src/responses/make.py !}
```

By default, the `make_response` returns a [JSONResponse](#jsonresponse) but that can be also
changed if the `response_class` parameter is set to something else.

So, why is this `make_response` different from the other responses? Well, here its where Lilya shines.

Lilya is pure Python, which means that it does not rely or depend on external libraries like Pydantic,
msgspec, attrs or any other **but allows** you to [build a custom encoder](#build-a-custom-encoder) that
can later be used to serialise your response automatically and then passed to the `make_response`.

Check the [build a custom encoder](#build-a-custom-encoder) and [custom encoders with make_response](#custom-encoders-and-the-make_response)
for more details and how to leverage the power of Lilya.

## Async content

You can pass coroutines as content to most standard responses. This will delay the evaluation of the content to the `__call__` method
if `resolve_async_content()` is not called earlier.
The cool part, we reuse the main eventloop.

Note, this means we get the body attribute of the response as well as the `content-length` header later
after the `resolve_async_content()` call (which is called in `__call__`).

## Delegate to Lilya

Delegating to Lilya means that if no response is specified, Lilya will go through the internal
`encoders` and will try to `jsonify` the response for you.

Let us see an example.

```python
{!> ../../../docs_src/responses/delegate.py !}
```

As you can see, no `response` was specified but instead a python `dict` was returned. What Lilya
internally does is to *guess* and understand the type of response parse the result into `json`
and returning a `JSONResponse` automatically,

If the type of response is not json serialisable, then a `ValueError` is raised.

Let us see some more examples.

```python
{!> ../../../docs_src/responses/delegate_examples.py !}
```

And the list goes on and on. Lilya by design understands almost every single datastructure of Python
by default, including `Enum`, `deque`, `dataclasses`, `PurePath`, `generators` and `tuple`.

This is archived by using [Encoders](encoders.md).
Mainly they are additional encoders for types tje json encoder cannot handle.


## Pass body types directly to the application server

By default `ASGI` allows only *byte strings* as body type.
Some servers are more lenient and allow also `memoryview`, `bytearray` or maybe something custom, which prevent
in best case a copy. If you want to leverage this you can use `passthrough_body_types`. It is a type tuple on the response
which contains the types which are directly forwarded to the application server.
Please add `bytes` always to the types tuple, otherwise if you return bytes, it could be returned base64 encoded.

To pass them through you have three options:

1. Subclassing the response and add `passthrough_body_types` either as ClassVar, assignment on initialization or as property.
2. Some responses allow setting `passthrough_body_types` on the fly. Pass the wanted types tuple to it.
3. Overwrite globally the types tuple in `lilya.responses.Response`. This is not recommended for libraries only for final applications.
