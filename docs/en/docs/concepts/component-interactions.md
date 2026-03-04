# Component Interactions

This page shows how Lilya components collaborate at runtime.

## System architecture

```mermaid
flowchart LR
    Client[Client] --> Server[ASGI server]
    Server --> App[Lilya app]

    Settings[Settings layer] --> App
    App --> MW[Middleware chain]
    MW --> Router[Router]
    Router --> Include[Include and Host]
    Include --> Route[Path and WebSocketPath]

    Route --> DI[Dependency resolution]
    DI --> Perm[Permission chain]
    Perm --> Handler[Handler]

    Handler --> Enc[Encoder and Response]
    Enc --> Server
```

## Component interaction graph

```mermaid
flowchart TB
    Root[Root Lilya] --> SharedMW[Global middleware]
    Root --> UsersInc[Include /users]
    Root --> BillingInc[Include /billing]

    UsersInc --> UsersApp[ChildLilya Users]
    BillingInc --> BillingApp[ChildLilya Billing]

    UsersApp --> UsersDeps[Users dependencies]
    BillingApp --> BillingDeps[Billing dependencies]

    UsersDeps --> UsersRoutes[Users routes]
    BillingDeps --> BillingRoutes[Billing routes]
```

## Use this model to decide boundaries

- Use `Include` for feature grouping
- Use `ChildLilya` for stronger module boundaries
- Keep shared concerns centralized, feature concerns local

## Related reference pages

- [Architecture Overview](../architecture.md)
- [Routing](../routing.md)
- [Introspection](../introspection.md)

## Next steps

- [Build a Modular API](../tutorials/build-a-modular-api.md)
