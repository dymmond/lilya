# Dependency Injection

Welcome to the definitive guide for using dependency injection in Lilya. In this document, we'll explore
how to leverage the `Provide` and `Provides` primitives to cleanly manage shared resources, services, and configuration across your application,
includes (sub-applications), and individual routes.

## Why Dependency Injection?

Dependency injection helps:

* **Decouple** business logic from infrastructure.
* **Reuse** services (e.g., database sessions, caches) without reinitializing them per request.
* **Override** behavior in testing or in specific sub-applications without changing core code.
* **Compose** complex services by injecting one into another (e.g., a token provider that needs a client).

Lilya's lightweight DI makes these patterns straightforward, whether at the app level, include (module) level, or individual route level.

---

## Core Primitives

### `Provide`

Use in your `Lilya(...)` or `Include(...)` constructor to register how to build a dependency. Signature:

```python
{!> ../../../docs_src/dependencies/example1.py !}
```

Options:

* `use_cache=True/False` (default `False`): cache the factory result for the lifetime of a request.

#### Without `Provide`

Lilya also allows you to pass without `Provide` and internally it will wrap it in a `Provide` object
for you.

This of course comes with its limitations. The flags such as `use_cache` cannot be injected as if you declare
`Provide` directly.

Is this useful? It it on a case by case basis but it shows once again how flexible Lilya can be.

```python
{!> ../../../docs_src/dependencies/example1_no_provide.py !}
```

### `Provides`

Use in your handler signature to declare that a parameter should be injected:

```python
{!> ../../../docs_src/dependencies/provides.py !}
```

Behind the scenes, Lilya collects all `Provide` maps from app → include → route, then calls each factory in dependency order.

!!! Tip
    As from version 0.16.5, Lilya is able to discover the dependencies in a more automated manner without the need or use
    of the `Provides` but using the `Provides` will always be available for any possible edge case you might find.

#### Dependency Injection Behavior

Lilya supports flexible dependency injection for both HTTP and WebSocket handlers. Dependencies can be declared explicitly using `Provides()` or injected implicitly via fallback if defined in the app or route configuration.

##### Injection Scenarios

The following table summarizes how dependencies are handled based on how they are declared in the handler and whether they are available in the app's `dependencies` mapping.

##### HTTP & WebSocket Handlers

Here is an example using `session` (can be a database session) as a dependency.

| Declaration Style                  | Declared in handler | Declared in `dependencies` | Injected? | Error if missing? | Notes                        |
|-----------------------------------|----------------------|-----------------------------|-----------|-------------------|------------------------------|
| `session=Provides()`              | ✅ Yes               | ✅ Yes                      | ✅ Yes    | ❌ No             | Explicit opt-in              |
| `session=Provides()`              | ✅ Yes               | ❌ No                       | ❌ No     | ✅ Yes            | Required but missing         |
| `session: Any`                    | ❌ No                | ✅ Yes                      | ✅ Yes    | ❌ No             | Fallback injection           |
| `session: Any`                    | ❌ No                | ❌ No                       | ❌ No     | ❌ No             | Skipped silently             |
| `session: Any = None`            | ❌ No                | ✅ Yes                      | ✅ Yes    | ❌ No             | Fallback + default value     |
| `session` (no type, no default)   | ❌ No                | ✅ Yes                      | ✅ Yes    | ❌ No             | Fallback injection           |

##### Key Rules

- **Explicit injection** using `Provides()` makes the dependency required. If it's missing, an error is raised.
- **Fallback injection** occurs when a parameter is:
    - Present in `dependencies`, and
    - Declared in the handler without a default (`inspect.Parameter.empty`).
- If a fallback dependency is not found, it is **silently skipped**.
- You can still provide default values (e.g. `= None`) to make parameters optional even if not injected.

##### Example

```python
# App config
app = Lilya(dependencies={"session": Provide(get_session)})

# Handler with explicit injection
async def handler(session=Provides()):
    ...

# Handler with fallback injection
async def handler(session: Session):
    ...

# Handler with fallback + default
async def handler(session: Session = None):
    ...
```

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

## Depends and `inject`

What if you simply want to use a dependency injection that simply does not rely on a `request`/`response` lifecycle?

For example, you have in your code some something that simply needs to run without it, example? A scheduler task?

Of course you do have more examples other than this one.

Well, Lilya now comes equipped with this possibility with a new `Depends` and `@inject` decorator.

```python
from lilya.dependencies import Depends, inject
```

### `Depends`

Although the name might sounds familiar to a few, if not a lot of people, in Lilya world `Depends` is similar to `Resolve`
but operates on an *requestless* world.

For the `Depends` to work you will also need to have the `@inject` decorator to help you out.

Let us go into an example. Let us assume you have some sort of scheduler running and you would need a database session
to connect and perform some sort of operations.

Now, as you can see, you don't need a request/response for this, do you? (Celery tasks, for example?)

So you would have something like this:

```python
{!> ../../../docs_src/dependencies/depends/conn.py !}
```

So far so good, right?

You can use the `get_db` inside your [Provide](#provide) or [Resolve](#the-resolve-dependency-object) as this can be
injected into your handlers **but you cannot use it just like this if you need inside a task**, can you?

Ok, this is where the `Depends` and `@inject` come to play.

Let us update the example to add an extra function that can then be used outside the request/response cycle.

```python
{!> ../../../docs_src/dependencies/depends/conn_updated.py !}
```

Did you notice the new `get_database_session` function? Well, this is how it works, you can now use
that function everywhere in your code and it will perform the dependency injection as you are used.

This is great as you can have normal Python functions that simply do not care about request lifecycle but
you still want to use some sort of dependency injection for a myriad of reasons.

This new `Depends` and `@inject` will allow you to do just that and it will take care of generators,
scopes and so on as usual.

---

## Best Practices

* **Keep factories pure**: avoid side effects outside creating the dependency.
* **Cache** long-lived resources (DB sessions, HTTP clients).
* **Group dependencies** by include for modular design.
* **Override sparingly** at route level—for true variations only.
* **Document** which dependencies each handler needs with clear parameter names.
* `Depends` and `inject` are used **outside** the request/response cycle and must not be mistaken for the rest.

With these patterns, you'll keep your Lilya code clean, testable, and maintainable.
