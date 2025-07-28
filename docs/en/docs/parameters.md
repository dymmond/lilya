# Query Parameters

Query parameters are an essential part of API development in Lilya, allowing you to extract dynamic
values from the **query string** of an HTTP request. This guide explains what query parameters are,
why and when to use them, and how Lilya makes it simple and elegant to declare and inject them into your
endpoint logic.

---

## What Are Query Parameters?

Query parameters are key-value pairs passed at the end of a URL after the `?` symbol.
They are used to filter, search, paginate, or otherwise customize the data returned by an API.

For example:

```

GET /items?category=books\&limit=10

````

Here, `category` and `limit` are query parameters.

---

## Why Use Query Parameters?

- **Filtering results:** e.g., `?status=active`
- **Pagination:** e.g., `?page=2&limit=20`
- **Searching:** e.g., `?query=laptop`
- **Optional values:** for things that are not required in the URL path
- **Stateless design:** clients can change the request behavior without altering the endpoint structure

---

## Benefits of Lilya's Parameter System

- **Declarative:** Declare query parameters directly in your function signature
- **Type-safe:** Parameters are automatically cast to the correct types
- **Optional and required support:** You can control whether a param is optional or required
- **Cleaner APIs:** Avoid manual extraction from the request object

---

## Declaring Query Parameters

You can declare a query parameter using the `Query` class:

```python
from lilya.params import Query

async def get_user(name: str = Query(), age: int = Query(default=30)):
    ...
````

* If you omit `default`, it will default to `None`.
* You can also use `required=True` to enforce presence.

---

## Examples

### Example 1: Basic Query Injection

```python
from lilya.params import Query

async def search_books(query: str = Query()):
    return {"query": query}
```

Request:

```
GET /search?query=python
```

Response:

```json
{
  "query": "python"
}
```

---

### Example 2: Required vs Optional Parameters

```python
async def search(
    q: str = Query(required=True),
    page: int = Query(default=1),
):
    return {"q": q, "page": page}
```

* `q` is **required** — missing it will raise an error
* `page` defaults to `1` if not provided

---

### Example 3: Query + Path + Body + Dependency

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.params import Query
from lilya.dependencies import Provide
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

class Service:
    def show(self):
        return "test"

async def handle_user(
    user: User,                # Inferred from body
    name: str,                 # Inferred from path
    service: Service,          # Injected via Provide(...)
    q: str = Query()           # Inferred from query string
):
    return {
        "user": user.model_dump(),
        "name": name,
        "service": service.show(),
        "search": q
    }

app = Lilya(
    routes=[
        Path("/", handle_user)
    ],
    dependencies={
        "service": Provide(Service)
    }
)
```

Request:

```
GET /lilya?q=python
Body: {"name": "lilya", "age": 2}
```

Response:

```json
{
  "user": {"name": "lilya", "age": 2},
  "name": "lilya",
  "service": "test",
  "search": "python"
}
```

---

## How Lilya Resolves Parameters

When Lilya resolves parameters, it classifies them by:

* **Path-bound**: Automatically from the route (`/{name}`)
* **Query-bound**: If declared with `Query(...)`
* **Body-bound**: Any `BaseModel` not matched to another source
* **Dependencies**: Declared via `Provide(...)` or `Provides(...)`

This helps prevent incorrect assumptions and ensures each parameter comes from the correct place in the request
lifecycle.

---

## 📌 Summary

* Use `Query()` to declare query-bound parameters
* Control optionality with `default` and `required`
* Combine with path and body params for powerful, clean APIs
* Lilya automatically wires everything with type safety

---
