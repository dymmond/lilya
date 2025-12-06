# Lifecycle Events

Lilya provides a **powerful and explicit lifecycle system** to help you run logic at specific points in your application's lifetime,
such as connecting to databases, initializing caches, or performing cleanup before shutdown.

Lifecycle hooks exist at **three levels**:

1. **Global hooks** – Registered once for all apps.
2. **App hooks** – Specific to a `Lilya` or `ChildLilya` instance.
3. **Custom lifespan managers** – Using `@asynccontextmanager`.

## Global Lifecycle Hooks

Global hooks are declared once and automatically injected into every `Lilya` or `ChildLilya` instance.

They are defined using decorators from `lilya.lifecycle`:

```python
from lilya.lifecycle import on_startup, on_shutdown

@on_startup
async def connect_global_services():
    print("Connecting to global services...")

@on_shutdown
async def disconnect_global_services():
    print("Shutting down global services...")
```

These hooks are executed **before any app starts up**, and after every app shuts down.

**Order of execution:**

| Phase    | Order        |
| -------- | ------------ |
| Startup  | Global -> App |
| Shutdown | App -> Global |

## App-Level Hooks (`on_startup` / `on_shutdown`)

Each `Lilya` (or `ChildLilya`) app can define its own lifecycle hooks, which run only for that app instance.

These are passed directly to the app constructor:

```python
from lilya.apps import Lilya
from lilya.responses import PlainText
from lilya.routing import Path

async def connect_db():
    print("Connecting to database...")

async def disconnect_db():
    print("Closing database connection...")

async def home():
    return PlainText("Hello, world!")

app = Lilya(
    routes=[Path("/", home)],
    on_startup=[connect_db],
    on_shutdown=[disconnect_db],
)
```

When Lilya starts, it automatically runs:

```
global_startup -> connect_db
```

and on shutdown:

```
disconnect_db -> global_shutdown
```

---

## ChildLilya Applications

You can structure large applications using modular **ChildLilya** instances.

Each `ChildLilya` has its own independent lifecycle hooks.
When included in a parent app, its lifecycle does **not** automatically trigger.
This isolation prevents unintended side effects when composing apps.

```python
from lilya.apps import Lilya, ChildLilya
from lilya.routing import Path, Include
from lilya.responses import PlainText

async def child_startup():
    print("Child app started")

async def child_shutdown():
    print("Child app stopped")

child = ChildLilya(
    routes=[Path("/", lambda: PlainText("Hello from child!"))],
    on_startup=[child_startup],
    on_shutdown=[child_shutdown],
)

app = Lilya(
    routes=[Include("/child", app=child)]
)
```

In this example:

* Starting the parent app will **not** trigger the child's lifecycle.
* If the `ChildLilya` runs independently, its hooks will execute normally.

This design gives you **predictable and modular control** over your app lifecycles.

## Using a Custom Lifespan Context

Instead of using startup/shutdown hooks separately, you can define a single **lifespan context manager** that handles both.

```python
from contextlib import asynccontextmanager
from lilya.apps import Lilya

@asynccontextmanager
async def lifespan(app):
    print("Startup logic")
    yield
    print("Shutdown logic")

app = Lilya(lifespan=lifespan)
```

This is a clean, async-native way to manage setup and teardown in a single, elegant block.

## When to Use What

| Use Case                                                    | Recommended Mechanism                     |
| ----------------------------------------------------------- | ----------------------------------------- |
| Global service initialization (e.g., telemetry, tracing)    | `@on_startup` / `@on_shutdown` decorators |
| Per-app setup (e.g., DB, cache, per-instance configuration) | `on_startup` / `on_shutdown` in `Lilya()` |
| Highly customized setup or teardown flow                    | `lifespan` context manager                |
| Modular, reusable sub-apps                                  | `ChildLilya` with isolated hooks          |

## Full Example

```python
from contextlib import asynccontextmanager
from lilya.apps import Lilya, ChildLilya
from lilya.routing import Path, Include
from lilya.responses import PlainText
from lilya.lifecycle import on_startup, on_shutdown

@on_startup
def init_telemetry():
    print("Telemetry started")

@on_shutdown
def stop_telemetry():
    print("Telemetry stopped")

async def main_startup():
    print("Main DB connected")

async def main_shutdown():
    print("Main DB disconnected")

async def child_startup():
    print("Child cache ready")

async def child_shutdown():
    print("Child cache flushed")

child_app = ChildLilya(
    routes=[Path("/", lambda: PlainText("Hello from child!"))],
    on_startup=[child_startup],
    on_shutdown=[child_shutdown],
)

app = Lilya(
    routes=[Include("/child", app=child_app)],
    on_startup=[main_startup],
    on_shutdown=[main_shutdown],
)

# Expected output when running app
"""
Telemetry started
Main DB connected
<app serving>
Main DB disconnected
Telemetry stopped
"""
```

## Summary

* **Global hooks** – Registered with decorators, run for every app.
* **App hooks** – Defined per `Lilya` or `ChildLilya` instance.
* **Independent lifecycles** – No cross-triggering between parent and child apps.
* **Optional `lifespan`** – For advanced setup/teardown logic.
