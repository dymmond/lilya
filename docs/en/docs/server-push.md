# Server Push

Lilya incorporates support for `HTTP/2` and `HTTP/3` server push,
enabling the proactive delivery of resources to the client for accelerating page load times.

## The method

This method is employed to initiate a server push for a resource.
If server push functionality is not available, this method takes no action.

- `path`: A string specifying the path of the resource.

```python
{!> ../../../docs_src/push/server.py !}
```

## Availability and checks

Server push depends on ASGI server support for the `http.response.push` extension.

You can check support from request/connection scope data with:

* `request.is_server_push`

If support is unavailable, `await request.send_push_promise(...)` is safely ignored.

## Practical notes

* Use push only for assets that are very likely needed immediately.
* Avoid pushing large assets blindly.
* Measure real browser behavior before relying on push for performance gains.
