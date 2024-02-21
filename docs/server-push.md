# Server Push

Lilya incorporates support for `HTTP/2` and `HTTP/3` server push,
enabling the proactive delivery of resources to the client for accelerating page load times.

## The method

This method is employed to initiate a server push for a resource.
If server push functionality is not available, this method takes no action.

- `path`: A string specifying the path of the resource.

```python
{!> ../docs_src/push/server.py !}
```
