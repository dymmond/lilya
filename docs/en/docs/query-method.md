# HTTP QUERY

`QUERY` is an HTTP method standardized by [RFC 10008](https://www.rfc-editor.org/rfc/rfc10008.html).
It is designed for read-only operations where the query input is too large, too structured, or too
sensitive to fit naturally in the URL.

RFC 10008 defines `QUERY` as safe and idempotent. A `QUERY` request asks the target resource to
process the enclosed content and return the result without changing the target resource state.
The request content has defined meaning for `QUERY`, unlike a `GET` request body.

## When to use QUERY

Use `QUERY` instead of `GET` when the operation is read-only but the query input does not belong in
the URI:

* The encoded URI could exceed practical client, proxy, or server limits.
* The input is structured, such as JSON filters or a domain query language.
* The input is better kept out of URLs because URLs are commonly logged or bookmarked.

Use `QUERY` instead of `POST` when the operation is not a mutation. `POST` does not communicate
safe and idempotent semantics by itself, while `QUERY` does. Do not use `QUERY` for create, update,
delete, submit, payment, login, or any other operation where the client asks the server to change
application state.

## Define a QUERY Route

Use the `query()` decorator for a single-method route:

```python
from lilya.apps import Lilya
from lilya.requests import Request

app = Lilya()


@app.query("/search")
async def search(request: Request):
    filters = await request.json()
    return {"filters": filters}
```

You can also use the generic route APIs:

```python
from lilya.routing import Path

routes = [
    Path("/search", handler=search, methods=["QUERY"]),
]
```

`QUERY` is matched as its own method. A `GET` request will not match a `QUERY` route, and a `QUERY`
request will not match a `POST` route.

## Send a Body

Lilya exposes `QUERY` request bodies through the same request APIs used by other methods:

```python
@app.query("/reports")
async def reports(request: Request):
    body = await request.body()
    return {"size": len(body)}
```

For JSON:

```python
@app.query("/items")
async def items(request: Request):
    query = await request.json()
    return {"query": query}
```

RFC 10008 requires servers to fail `QUERY` requests when `Content-Type` is missing or inconsistent
with the request content. Lilya makes the method, headers, and body available to handlers and
middleware; validate the query media type in your endpoint or a reusable dependency/middleware when
your API only accepts specific query formats.

## Test Client

Use the dedicated helper:

```python
response = client.query("/items", json={"where": {"status": "active"}})
assert response.status_code == 200
```

The generic request API also works:

```python
response = client.request("QUERY", "/items", content=b"select=name&limit=10")
```

`AsyncTestClient` provides the same `query()` helper:

```python
response = await client.query("/items", json={"limit": 10})
```

## Middleware, CSRF, and CORS

Middleware receives `scope["method"] == "QUERY"` and `request.method == "QUERY"`.

Because `QUERY` is safe by definition, `CSRFMiddleware` treats it as a safe method by default.
`CORSMiddleware(allow_methods=["*"])` includes `QUERY` in the generated allow-methods list.

## OpenAPI

Lilya includes `QUERY` routes in generated OpenAPI output using the lowercase `query` operation key
and emits `requestBody` metadata when you document a body with `@openapi(request_body=...)`.

Some OpenAPI tooling may lag behind RFC 10008 and may not recognize `query` as a path operation key
yet. The route still works at runtime; check your documentation renderer and client generator before
depending on generated clients for `QUERY` endpoints.

## Client and Proxy Support

`QUERY` is new. Some clients, browsers, proxies, gateways, and observability tools may not recognize
it yet, may require explicit allow-lists, or may not support sending a body with this method. Test the
full request path for production deployments, especially through reverse proxies, API gateways, WAFs,
and generated SDKs.
