# `jsonify`

The `jsonify` helper in Lilya makes it simple to return JSON responses from your endpoints,
similar to Flask’s `jsonify`.

It automatically encodes Python objects into JSON, sets the correct `Content-Type`,
and allows you to customize status codes, headers, and cookies.

---

## When to Use `jsonify`

Use `jsonify` when you want to:

* Return JSON from your endpoints without manually creating a `Response`.
* Pass dicts, lists, or keyword arguments directly.
* Control status codes, headers, or cookies in a JSON response.
* Make migration from Flask smoother.

---

## Basic Example

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.responses.json import jsonify

async def hello(request):
    return jsonify(message="Hello, World!", status="ok")

app = Lilya(routes=[
    Path("/hello", hello)
])
```

Request:

```bash
curl http://localhost:8000/hello
```

Response:

```json
{"message": "Hello, World!", "status": "ok"}
```

---

## Returning Lists

If you pass a list or multiple arguments, they will be returned as JSON arrays:

```python
async def numbers(request):
    return jsonify([1, 2, 3])

async def multi(request):
    return jsonify(1, 2, 3)
```

* `/numbers` → `[1, 2, 3]`
* `/multi` → `[1, 2, 3]`

---

## Custom Status Codes

You can return custom HTTP status codes:

```python
async def created_user(request):
    return jsonify(id=1, name="Alice", status="created", status_code=201)
```

Response:

* Status → `201 Created`
* Body → `{"id": 1, "name": "Alice", "status": "created"}`

---

## Adding Headers

Custom headers can be added easily:

```python
async def with_headers(request):
    return jsonify(
        message="Hello",
        headers={"X-App-Version": "1.0"}
    )
```

Response will include:

```
X-App-Version: 1.0
```

---

## Adding Cookies

You can also set cookies directly:

```python
async def with_cookie(request):
    return jsonify(
        message="Hello",
        cookies={"session": "abc123"}
    )
```

Response will include:

```
Set-Cookie: session=abc123; Path=/
```

---

## Error Handling

It’s not allowed to mix both positional arguments and keyword arguments:

```python
# ❌ This raises TypeError
return jsonify({"a": 1}, b=2)
```

---

## API Reference

```python
jsonify(
    *args: Any,
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> Response
```

### Parameters

* **`*args`** – A single dict, list, or multiple values (converted to a list).
* **`status_code`** – Custom HTTP status code (default: 200).
* **`headers`** – Optional dictionary of response headers.
* **`cookies`** – Optional dictionary of cookies to set.
* **`**kwargs`** – Treated as a dict payload if no `*args` provided.

with `jsonify`, Lilya makes returning JSON **fast, safe, and friendly**, while adding async-native power.
