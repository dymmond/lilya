# Responses

Lilya provides several lightweight response helpers under
`lilya.contrib.responses.shortcuts` to make endpoint development faster and cleaner.

These shortcuts let you quickly send JSON, streaming, or empty responses
without explicitly importing or instantiating `Response` classes.

### `send_json()`

```python
from lilya.contrib.responses.shortcuts import send_json
```

#### Description

Returns a `JSONResponse` object directly, allowing you to respond with structured data
in one line.

#### Example

```python
from lilya.contrib.responses.shortcuts import send_json

async def get_user(request):
    user = {"id": 1, "name": "Alice"}
    return send_json(user)
```

#### Parameters

| Name          | Type            | Description                        |                                   |
| ------------- | --------------- | ---------------------------------- | --------------------------------- |
| `data`        | `dict           | list`                              | The JSON-serializable payload.    |
| `status_code` | `int`           | HTTP status code (default: `200`). |                                   |
| `headers`     | `dict[str, str] | None`                              | Optional HTTP headers to include. |

#### Behavior

- Serializes `data` into JSON.
- Automatically sets `Content-Type: application/json`.
- Returns a ready-to-send `JSONResponse` instance.

#### Returns

`JSONResponse`: the response containing the serialized JSON payload.

### `json_error()`

```python
from lilya.contrib.responses.shortcuts import json_error
```

#### Description

Returns a structured JSON error payload without raising an exception.
This is ideal for explicit, graceful error responses inside your logic
(whereas `abort()` should be used to immediately stop request processing).

#### Example

```python
from lilya.contrib.responses.shortcuts import json_error

async def validate_user(request):
    data = await request.json()
    if "email" not in data:
        return json_error("Missing email field", status_code=422)
```

#### Parameters

| Name          | Type            | Description                        |                                         |
| ------------- | --------------- | ---------------------------------- | --------------------------------------- |
| `message`     | `str            | dict`                              | The error message or full JSON payload. |
| `status_code` | `int`           | HTTP status code (default: `400`). |                                         |
| `headers`     | `dict[str, str] | None`                              | Optional custom headers.                |

#### Behavior

* If `message` is a string, wraps it as `{"error": message}`.
* If `message` is a dict, uses it directly.
* Produces a `JSONResponse` without interrupting execution.

#### Returns

`JSONResponse`: the structured error payload.

### `stream()`

```python
from lilya.contrib.responses.shortcuts import stream
```

#### Description

Creates a `StreamingResponse` from any iterable or async generator.
Useful for large or continuous data streams such as logs, progress updates,
or server-sent events.

#### Example – Async Generator

```python
from lilya.contrib.responses.shortcuts import stream
import anyio

async def numbers(request):
    async def generator():
        for i in range(5):
            yield f"Number: {i}\\n"
            await anyio.sleep(1)

    return stream(generator(), mimetype="text/plain")
```

#### Example – Sync Generator

```python
def stream_lines(request):
    def generate():
        for i in range(3):
            yield f"Line {i}\\n"
    return stream(generate())
```

#### Parameters

| Name       | Type            | Description                                           |                   |
| ---------- | --------------- | ----------------------------------------------------- | ----------------- |
| `content`  | `Any`           | Iterable or async iterable yielding `bytes` or `str`. |                   |
| `mimetype` | `str`           | MIME type of the stream (default: `"text/plain"`).    |                   |
| `headers`  | `dict[str, str] | None`                                                 | Optional headers. |

#### Behavior

- Works with both sync and async generators.
- Sends incremental chunks as they are yielded.
- Uses AnyIO to support `asyncio` and `trio` transparently.

#### Returns

`StreamingResponse`: the active streaming response.

### `empty()`

```python
from lilya.contrib.responses.shortcuts import empty
```

#### Description

Returns an empty `Response` object, typically for actions that don’t need to return content
(such as `DELETE`, `PUT`, or successful `POST` endpoints that redirect elsewhere).

#### Example

```python
from lilya.contrib.responses.shortcuts import empty

async def delete_user(request):
    # Perform deletion...
    return empty()  # 204 No Content
```

#### Parameters

| Name          | Type            | Description                        |                   |
| ------------- | --------------- | ---------------------------------- | ----------------- |
| `status_code` | `int`           | HTTP status code (default: `204`). |                   |
| `headers`     | `dict[str, str] | None`                              | Optional headers. |

#### Behavior

- Creates a minimal response with no body.
- Sets `Content-Length: 0` automatically.

#### Returns

`Response`: an empty HTTP response.

### When to Use These Shortcuts

| Use Case                            | Shortcut       |
| ----------------------------------- | -------------- |
| Returning structured data           | `send_json()`  |
| Returning an error payload          | `json_error()` |
| Sending live or large output        | `stream()`     |
| Returning no content (e.g., DELETE) | `empty()`      |

### Comparison with [`abort()`](./abort.md)

| Shortcut       | Purpose                                                    | Raises Exception? |
| -------------- | ---------------------------------------------------------- | ----------------- |
| `abort()`      | Immediately stops execution with an `HTTPException`.       | ✅ Yes             |
| `json_error()` | Returns an error payload explicitly (execution continues). | ❌ No              |
| `send_json()`  | Normal JSON response for successful operations.            | ❌ No              |
| `stream()`     | Streams chunks of data incrementally.                      | ❌ No              |
| `empty()`      | Indicates success with no body.                            | ❌ No              |
