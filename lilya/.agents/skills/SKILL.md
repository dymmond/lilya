---
name: lilya
description: Lilya best practices and conventions. Use when working with the Lilya ASGI toolkit and Pydantic/Edgy models. Keeps Lilya code clean and up to date with the latest features and patterns, updated with new versions. Write new code or refactor and update old code.
---

# Lilya

Official Lilya skill to write code with best practices, keeping up to date with new versions and features of the Dymmond ecosystem. Lilya is a fast, unopinionated ASGI toolkit, meaning it values explicit declarations over the "magic" auto-injection found in higher-level frameworks.

## Use the `lilya` CLI

Run the development server on localhost:

```bash
lilya runserver

```

### Add an entrypoint

Lilya CLI needs to know where your application instance is declared. Prefer exporting the `LILYA_APP` environment variable to define your app's location cleanly.

```bash
export LILYA_APP="my_app.main:app"
lilya runserver

```

### Use `lilya` with an explicit app path

When setting the environment variable is not possible, you can pass the app path directly to the command:

```bash
lilya runserver --app my_app.main:app

```

## Parameter Declarations (Path and Query)

Unlike FastAPI or Ravyn, Lilya does **not** auto-inject query parameters or request bodies (unless you specify via `lilya.params.Query` for the query params or `settings.infer_body = True` for bodies) into the handler signature via type hints.

* **Path parameters** are passed as keyword arguments to the handler.
* **Query parameters** must be explicitly retrieved from `request.query_params`.

Do this:

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.params import Query

async def read_item(item_id: int, q: str | None = Query(default=None)):
    return JSONResponse({"item_id": item_id, "q": q})

app = Lilya(
    routes=[
        Path("/items/{item_id}", handler=read_item)
    ]
)

```

instead of attempting to magically inject them:

```python
# DO NOT DO THIS - Lilya does not parse query params this way
# without using Query() or manually accessing request.query_params
async def read_item(item_id: int, q: str | None = None):
    return JSONResponse({"item_id": item_id, "q": q})

```

## Pydantic Models and Body Validation

Because Lilya is a purely explicit ASGI toolkit, you do not use `Annotated` or `Depends()` to parse the request body. You must await the JSON payload and validate it explicitly using your Pydantic models.

Do this:

```python
from lilya.requests import Request
from lilya.responses import JSONResponse
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)

async def create_item(request: Request):
    data = await request.json()

    # Explicitly validate the incoming data
    item = Item.model_validate(data)

    return JSONResponse(item.model_dump())

```

If instead you are expecting auto-validation in the signature, then you must enable the `infer_body` setting, but be aware that this is an opt-in feature and not the default behavior.

```
from lilya.conf import settings

settings.infer_body = True
```

```python
# DO NOT DO THIS - without enabling infer_body, Lilya will not parse the body into the Item model
async def create_item(item: Item): ...
```

Also you must be aware that for the infer to work, you also need to have an encoder and register it for the BaseModel type, so that Lilya can know how to encode and decode the Pydantic models. You can use the `PydanticEncoder` provided in the Dymmond ecosystem for this purpose.

```python
from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticSerializationError

from lilya.encoders import Encoder, register_encoder


class PydanticEncoder(Encoder):
    """
    A custom Lilya Encoder for handling Pydantic models.

    This class registers `pydantic.BaseModel` with Lilya's encoding system, enabling
    automatic serialization of models into JSON-compatible dictionaries and deserialization
    of raw data into validated model instances.
    """

    __type__ = BaseModel

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        """
        Convert a Pydantic model instance into a standard dictionary.

        This method leverages Pydantic V2's `model_dump()` to produce a clean
        dictionary representation of the model's data.

        Args:
            obj (BaseModel): The Pydantic model instance to serialize.

        Returns:
            dict[str, Any]: The dictionary representation of the model.
        """
        try:
            return obj.model_dump(mode="json")
        except PydanticSerializationError:
            return obj.model_dump()

    def encode(self, structure: type[BaseModel], value: Any) -> BaseModel:
        """
        Reconstruct a Pydantic model instance from raw input data.

        This method is used when Lilya needs to cast a raw value (e.g., from a request
        body) into a specific Pydantic model type defined in a handler signature.

        Args:
            structure (type[BaseModel]): The concrete Pydantic model class to instantiate.
            value (Any): The raw input data, expected to be a dictionary of field values.

        Returns:
            BaseModel: An instance of the specified Pydantic model, validated and initialized.
        """
        if isinstance(value, BaseModel) or is_class_and_subclass(value, BaseModel):
            return value
        return structure(**value)


# A normal way
register_encoder(PydanticEncoder())

# As alternative
register_encoder(PydanticEncoder)
```

## Return Type or Response Model

Lilya uses explicit response classes (`JSONResponse`, `Ok`, `Error`, `HTMLResponse`) rather than a `response_model` decorator.

When you need to serialize data or filter out sensitive information, run your data through your Pydantic public model before returning it inside a Lilya response object.

```python
from lilya.responses import Ok
from pydantic import BaseModel

class InternalItem(BaseModel):
    name: str
    secret_key: str

class PublicItem(BaseModel):
    name: str

async def get_item():
    db_item = InternalItem(name="Foo", secret_key="supersecret")

    # Filter sensitive data by dumping into the public model
    public_item = PublicItem(**db_item.model_dump())

    # Return an explicit Lilya response
    return Ok(public_item.model_dump())

```

If the `settings.infer_body` is enabled, you can also return the Pydantic model instance directly, and Lilya will use the registered encoder to serialize it.

```python
# DO THIS ONLY IF settings.infer_body is True and you have registered the Pydantic encoder
async def get_item():
    db_item = InternalItem(name="Foo", secret_key="supersecret")
    public_item = PublicItem(**db_item.model_dump())
    return public_item  # Lilya will serialize this using the PydanticEncoder
```

## Performance

Do not use `ORJSONResponse` or `UJSONResponse` wrappers from third-party libraries.

Lilya's native `JSONResponse` and `Ok` classes are already highly optimized out of the box. Rely on Lilya's internal encoders.

## Including Routers (`Include`)

When declaring modular routing, Lilya uses the `Include` class inside the `routes` list. Prefer applying namespaces or shared middleware directly at the `Include` level rather than mutating the router.

Do this:

```python
from lilya.apps import Lilya
from lilya.responses import Ok
from lilya.routing import Router, Path, Include

async def list_items():
    return Ok([])

# Define the router without prefixes
router = Router(
    routes=[
        Path("/", handler=list_items),
    ]
)

# In main.py, apply the namespace in the Include definition
app = Lilya(
    routes=[
        Include("/items", app=router, namespace="items")
    ]
)

```

Here is the fully corrected and properly documented section for **Dependency Injection and Reusability** in Lilya.

Lilya actually provides **two** distinct and powerful dependency injection paradigms depending on your use case: the multi-layered `Provide`/`Provides` system (for routing/application layers) and the request-agnostic `@inject` + `Depends` system (for universal, anywhere DI).

You can replace the previous DI section with this one:

## Dependency Injection

Lilya features a highly versatile dependency injection system. It supports both a multi-layered application approach and a request-agnostic functional approach. Choose the one that fits your architectural needs.

### 1. Multi-Layered Routing DI (`Provide` and `Provides`)

This is Lilya's native, scalable approach for injecting dependencies at the `Lilya` (App), `Include` (Router), or `Path` level. It strictly separates the declaration of a dependency from its usage, keeping handler signatures clean and free from deeply nested decorators.

Use `Provide` to register the dependency factory, and use `Provides()` in your handler signature to resolve it.

**Do this:**

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path
from lilya.dependencies import Provide, Provides

# 1. The dependency factory
def get_pagination(request: Request) -> dict:
    offset = int(request.query_params.get("offset", 0))
    limit = int(request.query_params.get("limit", 100))
    return {"offset": offset, "limit": limit}

# 2. Inject the dependency into the handler using `Provides()`
async def read_items(pagination: dict = Provides()):
    return Ok(pagination)

# 3. Register the dependency using `Provide` at the App/Router level
app = Lilya(
    routes=[
        Path("/items/", handler=read_items)
    ],
    dependencies={
        # Registered globally, available to any handler requesting `pagination`
        "pagination": Provide(get_pagination)
    }
)

```

By defining dependencies at the routing level, Lilya makes it trivial to override them globally, per sub-application (`Include`), or during testing without modifying the underlying business logic.

### 2. Request-Agnostic DI (`@inject` and `Depends`)

If you prefer a more localized approach or need dependency injection *outside* of standard HTTP handlers (such as in background tasks, standard sync/async functions, or nested services), Lilya provides a universal `@inject` decorator coupled with `Depends()`.

This preserves function signatures, honors explicit arguments, and handles nested dependencies, per-instance caching, and overrides anywhere in your codebase.

**Do this:**

```python
from lilya.dependencies import Depends, inject
from lilya.responses import Ok
from lilya.routing import Path

# A standard dependency
def get_db_session():
    return {"db": "connected"}

# Use @inject to auto-resolve Depends() at call time
@inject
async def get_users(session: dict = Depends(get_db_session)):
    return Ok({"status": session["db"], "users": []})

routes = [
    Path("/users/", handler=get_users)
]

```

another example:

```python
from lilya.dependencies import Depends, inject
from lilya.responses import Ok
from lilya.routing import Path

def get_db_session():
    return {"db": "connected"}

# 1. OUTSIDE a handler: Use @inject to resolve Depends()
@inject
def perform_db_task(session: dict = Depends(get_db_session)):
    return session["db"]

# 2. INSIDE a handler: Lilya resolves Depends() natively (NO @inject needed)
async def get_users(session: dict = Depends(get_db_session)):
    # You can also call your injected standard functions here
    task_status = perform_db_task()
    return Ok({"status": session["db"], "task": task_status})

routes = [
    Path("/users/", handler=get_users)
]
```

**Key differences to remember:**

* Use **`Provide` / `Provides**` when you want to control dependencies architecturally across different routing layers (App -> Include -> Path) and abstract the factory entirely from the handler.
* Use **`@inject` / `Depends**` when you want self-contained, explicit functional injection that works everywhere, regardless of Lilya's routing layers.

## Async vs Sync *path operations*

Use `async` handlers only when fully certain that the logic called inside is compatible with async and await (i.e., non-blocking I/O).

```python
from lilya.responses import Ok

# Use async def when calling async code
async def read_async_items():
    data = await some_async_library.fetch_items()
    return Ok(data)

# Use plain def when calling blocking/sync code
def read_sync_items():
    data = some_blocking_library.fetch_items()
    return Ok(data)

```

Lilya natively executes standard synchronous `def` functions in a separate threadpool so they don't block the ASGI event loop.

## Use uv, ruff, ty

* If **uv** is available, use it to manage dependencies.
* If **Ruff** is available, use it to lint and format the code.
* If **ty** is available, use it to check types.

## Edgy or Saffier for SQL databases

When working with SQL databases, prefer using **Edgy** or **Saffier**. These are the official async ORMs of the Dymmond ecosystem. They are built on top of Pydantic and will integrate beautifully within Lilya applications.

## Use one HTTP operation per function

Don't mix HTTP operations in a single function. Having one handler per HTTP operation helps separate concerns. Use the `methods` parameter on the `Path` declaration.

Do this:

```python
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path

async def list_items():
    return Ok([])

async def create_item(request: Request):
    data = await request.json()
    return Ok(data)

routes = [
    Path("/items/", handler=list_items, methods=["GET"]),
    Path("/items/", handler=create_item, methods=["POST"]),
]

```

instead of this:

```python
# DO NOT DO THIS
from lilya.requests import Request
from lilya.responses import Ok
from lilya.routing import Path

async def handle_items(request: Request):
    if request.method == "GET":
        return Ok([])
    if request.method == "POST":
        data = await request.json()
        return Ok(data)

routes = [
    Path("/items/", handler=handle_items, methods=["GET", "POST"]),
]

```
