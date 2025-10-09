# Parameters

Lilya supports **Query**, **Header**, and **Cookie** parameters to cleanly and declaratively extract data
from HTTP requests.

1. **What** each parameter type is
2. **Why** and **when** to use them
3. **Benefits** of Lilya's parameter system
4. **How** to declare and inject them

---

## What Are Request Parameters?

* **Query Parameters**: Key‑value pairs in the URL after `?`, used for filtering, searching, pagination, and optional flags.
* **Header Parameters**: Metadata in HTTP headers (like `Authorization`, `X‑API‑TOKEN`), used for authentication, content negotiation, and custom flags.
* **Cookie Parameters**: Key‑value pairs stored in cookies, used for sessions, CSRF tokens, user preferences, and stateful data.

---

## ✅ Why Use Them?

* **Separation of concerns**: Clearly distinguish URL modifiers (query) from metadata (headers) and state (cookies).
* **Type safety**: Lilya casts and validates values automatically.
* **Declarative design**: Declare parameters in your function signature, not inside your handler code.
* **Consistency**: Uniform API for all parameter types with `required`, `default`, `alias`/`value`, and `cast` options.

---

## Benefits of Lilya's Parameter System

* **Clean signatures**: No manual extraction from `request`; Lilya handles it.
* **Automatic validation**: Missing required fields or invalid types immediately return 422.
* **Rich metadata**: Control `required`, set `default` or `alias`/`value`, and perform runtime `cast`.
* **Unified API**: Same workflow for `Query`, `Header`, and `Cookie` with minimal boilerplate.

---

## Declaration Syntax

### Query

```python
from lilya.params import Query

async def handler(
    q: str = Query(default=None, alias="q", required=False, cast=str)
):
    ...
```

| Option     | Type   | Description                    |
| ---------- | ------ | ------------------------------ |
| `default`  | `Any`  | Fallback if not present        |
| `alias`    | `str`  | Query key name in URL          |
| `required` | `bool` | Whether to enforce presence    |
| `cast`     | `type` | Callable to convert raw string |

---

### Header

```python
from lilya.params import Header

async def handler(
    token: str = Header(value="X-API-TOKEN", required=True, cast=str)
):
    ...
```

| Option     | Type   | Description                    |
| ---------- | ------ | ------------------------------ |
| `value`    | `str`  | Header key name (required)     |
| `required` | `bool` | Whether to enforce presence    |
| `cast`     | `type` | Callable to convert raw string |

---

### Cookie

```python
from lilya.params import Cookie

async def handler(
    session: str = Cookie(value="csrftoken", required=True, cast=str)
):
    ...
```

| Option     | Type   | Description                    |
| ---------- | ------ | ------------------------------ |
| `value`    | `str`  | Cookie name (required)         |
| `required` | `bool` | Whether to enforce presence    |
| `cast`     | `type` | Callable to convert raw string |

---

## 🔍 Real‑World Examples

### 1. Basic Query Injection

```python
async def search_books(query: str = Query()) -> dict:
    return {"query": query}
```

```http
GET /search?query=python
```

### 2. Header‑Based Auth

```python
async def get_user(
    token: str = Header(value="Authorization", required=True)
) -> dict:
    return {"user": validate_token(token)}
```

```http
GET /profile
Authorization: Bearer TOKEN123
```

### 3. Cookie‑Based Session

```python
async def dashboard(
    session_id: str = Cookie(value="sessionid", required=True)
) -> dict:
    return {"session": load_session(session_id)}
```

```http
GET /dashboard
Cookie: sessionid=abc123
```

### 4. Combined Query, Header, Cookie, Body, Dependency

```python
from lilya.params import Query, Header, Cookie
from lilya.dependencies import Provide
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

class Service:
    def show(self):
        return "ok"

async def handle(
    user: User,                          # from JSON body
    q: str = Query(alias="q", default="none"),
    token: str = Header(value="X-TOKEN", required=True),
    session: str = Cookie(value="csrftoken"),
    svc: Service = Provide(Service)      # injected dependency
):
    return {
        "user": user.model_dump(),
        "q": q,
        "token": token,
        "session": session,
        "svc": svc.show(),
    }
```

Request example:

```
GET /?q=hello
Headers: X-TOKEN: tok
Cookies: csrftoken=sess
Body: {"name": "tiago", "age": 35}
```

---

## Summary

* **Query**: URL-based filters/flags
* **Header**: HTTP metadata
* **Cookie**: Client‑stored data
* **Declare** with `Query`, `Header`, `Cookie` in signature
* **Control** `required`, `default`, `alias`/`value`, and `cast`
* **Combine** freely with path, body, and dependencies
