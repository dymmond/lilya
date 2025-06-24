# Dependency Injection

Welcome to the definitive guide for using dependency injection in Lilya. In this document, we’ll explore
how to leverage the `Provide` and `Provides` primitives to cleanly manage shared resources, services, and configuration across your application,
includes (sub-applications), and individual routes.

## Why Dependency Injection?

Dependency injection helps:

* **Decouple** business logic from infrastructure.
* **Reuse** services (e.g., database sessions, caches) without reinitializing them per request.
* **Override** behavior in testing or in specific sub-applications without changing core code.
* **Compose** complex services by injecting one into another (e.g., a token provider that needs a client).

Lilya’s lightweight DI makes these patterns straightforward, whether at the app level, include (module) level, or individual route level.

---

## Core Primitives

### `Provide`

Use in your `Lilya(...)` or `Include(...)` constructor to register how to build a dependency. Signature:

```python
{!> ../../../docs_src/dependencies/example1.py !}
```

Options:

* `use_cache=True/False` (default `False`): cache the factory result for the lifetime of a request.

### `Provides`

Use in your handler signature to declare that a parameter should be injected:

```python
{!> ../../../docs_src/dependencies/provides.py !}
```

Behind the scenes, Lilya collects all `Provide` maps from app → include → route, then calls each factory in dependency order.

---

## Application-Level Dependencies

### Example: Database Session

Imagine you have an async ORM and want to share a session per request:

```python
{!> ../../../docs_src/dependencies/db.py !}
```

* We register `db` globally, cached per request.
* Any route declaring `db = Provides()` receives the same session instance.

---

## Include-Level Dependencies

### Example: Feature Flag Service

Suppose you split your application into modules (includes) and each module needs its own feature-flag client:

```python
{!> ../../../docs_src/dependencies/service.py !}
```

Requests under `/admin` get the admin client; under `/public` get the public client—without manual passing.

---

## Route-Level Overrides

You can override an include or app dependency for a specific route.

### Example: A/B Test Handler

```python
{!> ../../../docs_src/dependencies/overrides.py !}
```

* Default group is `control`, but `/landing` sees `variant`.

---

## Nested Dependencies & Factories

Lilya resolves factories in topological order based on parameter names. Factories can themselves depend on other injections.

### Example: OAuth Token Injection

```python
{!> ../../../docs_src/dependencies/nested.py !}
```

* Lilya sees `token` depends on `client` and injects accordingly.

---

## Caching Behavior

By default, each factory runs once per request. If you pass `use_cache=True` to `Provide`, the result is reused in the same request context:

```python
Provide(expensive_io, use_cache=True)
```

Ideal for DB sessions, HTTP clients, or feature-flag lookups.

---

## Error Handling & Missing Dependencies

* **Missing**: if a handler requires `x=Provides()` but no `x` factory is registered → **500 Internal Server Error**.
* **Extra**: if you register `x` but no handler parameter uses `Provides()` → `ImproperlyConfigured` at startup.

Always match `Provide(...)` names with `Provides()` parameters.

## The Resolve dependency object

Lilya allows also to use what we call a "simpler" dependency injection. This dependency
injection system does not aim replace the `Provide` or `Provides` sytem but aims to provide another way of using some dependencies
in a simpler fashion in a non multi-layer fashion.

You can import directly from `lilya.dependencies`:

```python
from lilya.dependencies import Resolve
```

!!! Warning
    `Resolve()` is not designed to work on an [application level](#application-level-dependencies)
    as is. For application layers and dependencies, you **must still use the normal dependency injection system to make it work**
    or use the [Requires within the application layers](#resolve-within-the-application-layers)..

### A more detailed explanation

This is what Lilya describes as a simple dependency.

An example how to use `Resolve` would be something like this:

```python
{!> ../../../docs_src/dependencies/resolve/simple.py !}
```

This example is very simple but you can extend to whatever you want and need. The `Resolve` is not linked to any external library
but a pure Python class. You can apply to any other complex example and having a `Resolve` inside more `Resolve`s.

```python
{!> ../../../docs_src/dependencies/resolve/nested.py !}
```

### Resolve within the application layers

Now this is where things start to get interesting. Lilya operates in layers and **almost** everything works like that.

What if you want to use the `Resolve` to operate on a layer level? Can you do it? **Yes**.

It works as we normally declare dependencies using the `Provide` and `Provides`.

```python
{!> ../../../docs_src/dependencies/resolve/layer.py !}
```

---

## Best Practices

* **Keep factories pure**: avoid side effects outside creating the dependency.
* **Cache** long-lived resources (DB sessions, HTTP clients).
* **Group dependencies** by include for modular design.
* **Override sparingly** at route level—for true variations only.
* **Document** which dependencies each handler needs with clear parameter names.

With these patterns, you’ll keep your Lilya code clean, testable, and maintainable.
