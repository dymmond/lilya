# Exceptions & Exception Handlers

Exception handlers are, as the name suggests, the handlers in case an exception of type X occurs.

## Exception handlers

In every level the `exception_handler` parameter (among others) are available to be used and handle specific exeptions
raised on each level.

The exception handlers are read a python dictionary and you can pass the key as the exception itself or the `status_code`
that will always use the exception itself.

```python
{!> ../docs_src/exception_handlers/precedent.py !}
```

### What is happening

The application level contains an exception handler `handle_type_error` and the `handle_value_error` and that means that for
every `HTTPException` and `ValueError` being raised in the application it will be handled by that function.

### Custom exception handlers

We all know that Lilya handles really well the exceptions by design but sometimes we might also
want to throw an error while doing some code logic that is not directly related with a `data` of
an handler.

**Example**

```python
{!> ../docs_src/exception_handlers/example.py !}
```

This example is a not usual at all but it serves to show where an exception is raised.

Lilya offers **one** out of the box **custom exception handlers**:

* **handle_value_error** - When you want the `ValueError` exception to be automatically parsed
into a JSON.

```python
from lilya._internal._exception_handlers import handle_value_error
```

How it would look like the previous example using this custom exception handler?

```python
{!> ../docs_src/exception_handlers/example_use.py !}
```

## Using status codes

When declaring exception handlers, as mentioned before, you can use status codes instead of the
exception itself. This allows and indicates how an exception must be handle when a specific `status_code`
occurs.

This can be very useful if you only want to narrow down to `status_code` approach instead of the whole
`Exception` itself.

```python
{!> ../docs_src/exception_handlers/status_codes.py !}
```

## HTTPException

The `HTTPException` class serves as a foundational class suitable for handling various exceptions.
In the default `ExceptionMiddleware` implementation, plain-text HTTP responses are returned for any instance of `HTTPException`.

!!! Note
    The proper usage dictates that you exclusively raise `HTTPException` within routing or endpoints.
    Middleware and Permission classes, on the other hand, should simply return the appropriate responses directly.

## WebSocketException

The `WebSocketException` class is designed for raising errors specifically within WebSocket endpoints.
