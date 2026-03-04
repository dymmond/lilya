# ASGI Mental Model

Lilya is ASGI-first. Understanding ASGI's `scope`, `receive`, and `send` explains most Lilya behavior.

## Core contract

- `scope`: immutable connection/request metadata
- `receive`: inbound event stream (request body, websocket frames)
- `send`: outbound event stream (response start/body, websocket frames)

Lilya wraps this contract into higher-level abstractions such as:

- [Request](../requests.md)
- [Response](../responses.md)
- [WebSocket](../websockets.md)
- [Middleware](../middleware.md)

## How Lilya maps the contract

- App entry receives ASGI triplet
- Router resolves route chain
- Dependency and permission layers are applied
- Handler returns a response object or serializable value
- Response emits ASGI messages through `send`

## Why this matters

If you can reason about ASGI events, debugging middleware, streaming, websockets, and lifecycle hooks becomes predictable.

## Related concepts

- [Request Lifecycle](./request-lifecycle.md)
- [Layering and Precedence](./layering-and-precedence.md)

## Next steps

- [Request](../requests.md)
- [Middleware](../middleware.md)
