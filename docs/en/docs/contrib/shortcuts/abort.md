# `abort()`

This will immediately stop the request execution.

The `abort()` shortcut in Lilya lets you **immediately stop request processing** and raise an HTTP error response—exactly
like Flask's `abort()`, but async-native and fully integrated into Lilya's exception system.

It provides a concise, expressive way to signal HTTP errors from any handler, without manually raising or returning response objects.

## Quick Overview

```python
from lilya.contrib.responses.shortcuts import abort

async def endpoint():
    abort(404)  # immediately stop execution
```

When called, `abort()` raises an internal `HTTPException` that's automatically caught by Lilya's `ExceptionMiddleware`.
Depending on what arguments you pass, it can:

- Return a **default status phrase** (like `"Not Found"`)
- Include a **custom message** or **structured JSON body**
- Add **custom HTTP headers**
- Produce **any custom `Response`** type (e.g. `JSONResponse`, `HTMLResponse`, etc.)

## Function Signature

```python
def abort(
    status_code: int,
    detail: Any | None = None,
    headers: dict[str, Any] | None = None,
) -> None:
    ...
```

| Parameter       | Type                          | Description                                                                         |
| --------------- | ----------------------------- | ----------------------------------------------------------------------------------- |
| **status_code** | `int`                         | HTTP status code to return.                                                         |
| **detail**      | `Any` *(optional)*            | Body of the error response. Can be a string, dict, list, or any serializable value. |
| **headers**     | `dict[str, Any]` *(optional)* | Custom headers to include in the response.                                          |

## Basic Usage

### Raise a simple error

```python
from lilya.apps import Lilya
from lilya.contrib.responses.shortcuts import abort
from lilya.routing import Path

async def not_found():
    abort(404)

app = Lilya(routes=[Path("/item", not_found)])
```

**Result:**

```http
HTTP/1.1 404 Not Found
Content-Type: text/plain; charset=utf-8

Not Found
```

### Add a custom message

```python
async def forbidden(request):
    abort(403, "You cannot access this resource.")
```

**Result:**

```http
HTTP/1.1 403 Forbidden
Content-Type: text/plain; charset=utf-8

You cannot access this resource.
```

### Return structured JSON errors

```python
async def invalid(request):
    abort(400, {"error": "Invalid input", "field": "email"})
```

**Result:**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"error": "Invalid input", "field": "email"}
```

This is particularly useful in APIs or JSON driven endpoints.

### Add custom headers

```python
async def blocked(request):
    abort(403, "Access denied", headers={"X-Reason": "Policy Restriction"})
```

**Result:**

```http
HTTP/1.1 403 Forbidden
X-Reason: Policy Restriction
Content-Type: text/plain; charset=utf-8

Access denied
```

## Behavior Details

- When `detail` is a **dict** or **list**, `abort()` automatically wraps it in a `JSONResponse`.
- When `detail` is a **string**, it uses a plain `Response`.
- When `detail` is `None`, it returns the **standard HTTP phrase** for that status code (e.g. `"Not Found"`, `"Bad Request"`).
- For `204` or `304` responses, Lilya automatically sends **no body**, respecting HTTP semantics.

## Integration with custom exception handlers

You can still register your own exception handlers if you want full control:

```python
from lilya.apps import Lilya
from lilya.responses import JSONResponse
from lilya.exceptions import HTTPException

async def custom_http_exception(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

app = Lilya(exception_handlers={HTTPException: custom_http_exception})
```

Now `abort(401, "Unauthorized")` will trigger your custom handler and return a JSON response automatically.

## Example: API-style Errors

Here's a full working example showing `abort()` in a small API app.

```python
from lilya import Lilya
from lilya.routing import Path
from lilya.contrib.responses.shortcuts import abort

async def create_user(request):
    data = await request.json()
    if "email" not in data:
        abort(422, {"error": "Missing field", "field": "email"})
    return {"message": "User created"}

async def forbidden_zone():
    abort(403, "This endpoint is restricted.")

app = Lilya(
    routes=[
        Path("/users", create_user),
        Path("/admin", forbidden_zone),
    ]
)
```

**Example outputs:**

```
POST /users -> 422 {"error": "Missing field", "field": "email"}
GET  /admin -> 403 "This endpoint is restricted."
```

## Advanced: Raising Custom Responses

Since Lilya's `HTTPException` accepts a `response` parameter, you can attach **any Response subclass** directly:

```python
from lilya.responses import HTMLResponse
from lilya.exceptions import HTTPException

async def maintenance(request):
    html = "<h1>Service temporarily unavailable</h1>"
    response = HTMLResponse(html, status_code=503)
    raise HTTPException(status_code=503, response=response)
```

This bypasses the default text or JSON logic entirely.

## Summary

| Use Case                                    | Behavior                       |
| ------------------------------------------- | ------------------------------ |
| `abort(404)`                                | Returns 404 with `"Not Found"` |
| `abort(401, "Unauthorized")`                | Returns text message           |
| `abort(400, {"error": "Invalid"})`          | Returns JSON                   |
| `abort(403, "Blocked", {"X-Blocked": "1"})` | Adds custom headers            |
| `abort(204)`                                | No content body                |
| Custom `Response` in `HTTPException`        | Full control                   |


## See Also

- [Responses in Lilya](../../responses.md)
- [Exception Handling](../../exceptions.md)
- [send_file() Helper](../files/send-file.md)
