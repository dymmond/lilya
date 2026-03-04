# Request Lifecycle

This page describes the end-to-end HTTP flow in Lilya.

## Lifecycle sequence

```mermaid
sequenceDiagram
    participant C as Client
    participant S as ASGI Server
    participant A as Lilya App
    participant M as Middleware
    participant R as Router
    participant D as Dependencies
    participant P as Permissions
    participant H as Handler
    participant E as Encoder/Response

    C->>S: HTTP request
    S->>A: scope, receive, send
    A->>M: before_request hooks
    M->>R: dispatch
    R->>D: resolve dependencies
    D-->>H: injected arguments
    R->>P: evaluate permissions
    P-->>H: allow
    H->>E: return response/value
    E-->>S: ASGI response messages
    A->>M: after_request hooks
    S-->>C: HTTP response
```

## Execution phases

1. Inbound entry and middleware wrapping
2. Route matching and include/host resolution
3. Dependency resolution by layer
4. Permission checks
5. Handler execution
6. Response encoding and dispatch
7. Post-response hooks

## Related reference pages

- [Requests](../requests.md)
- [Routing](../routing.md)
- [Dependencies](../dependencies.md)
- [Permissions](../permissions.md)
- [Responses](../responses.md)

## Next steps

- [Layering and Precedence](./layering-and-precedence.md)
- [Troubleshooting](../troubleshooting.md)
