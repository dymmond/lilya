---
hide:
  - navigation
---

# OpenAPI

This document explains, in exhaustive detail, how to add and configure OpenAPI generation in a Lilya application. You will learn how to:

- Use the `@openapi` decorator on your handlers to declare summaries, descriptions, query parameters, and response models.
- Organize routes with `Path`, `Include`, and nested Lilya “child” apps.
- Generate a complete OpenAPI 3.x document (including paths, parameters, responses, and component schemas) by calling a single function.
- Handle common edge cases (path vs. query name collisions, typed catch‐all placeholders, arrays of models, etc.).
- Read and interpret the resulting OpenAPI JSON (or YAML) to serve Swagger UI, Redoc, or any other OpenAPI‐compatible documentation tool.

Although under the hood this integration uses several helper modules (for schema generation, placeholders stripping, and recursion),
**this document does not reference any internal utility filenames**. Rather, it focuses on the concepts, usage patterns,
and example code you will write in your Lilya app.

---

## First Steps

Lilya, on the contrary of vast majority of the frameworks, makes this integration as simple as possible and **optional**, this means
when you install Lilya, the **openapi** needs to be installed as well to work.

## Installation

To make it you simply need to run:

```shell
pip install lilya[openapi]
```

Why this? Well, Lilya uses Pydantic under the hood to generate JSON Schemas, and OpenAPI is a standard for describing RESTful APIs.
By installing the `openapi` extra, you get all the necessary dependencies and modules to enable OpenAPI generation in your Lilya application.

## Why OpenAPI?

- **Standardized Documentation**: OpenAPI (formerly Swagger) is the de-facto standard for describing RESTful APIs.
It lets you auto-generate interactive documentation (e.g. Swagger UI, Redoc, Rapidoc..), generate client libraries in multiple languages, and validate requests/responses.
- **Ease of Use**: By decorating Lilya handlers and calling a single function, you get a fully-compliant OpenAPI 3.x specification.
No manual JSON or YAML editing is required.
- **Discoverability**: Tools like Swagger UI let developers explore endpoints, parameters, request/response shapes, and try them out directly from the browser.
- **Interoperability**: Many API gateways, testing frameworks, and code generators expect an OpenAPI spec.

---

## Annotating Handlers with `@openapi`

The `@openapi` decorator is the user-facing way to declare metadata for your HTTP handlers. It collects information about summaries,
descriptions, query parameters, and response schemas, and stores them on the function for later consumption by the generator.

### Basic Handler Example

```python
{!> ../../../docs_src/openapi/example.py !}
```

* **What happens?**

* `@openapi(summary="Hello endpoint")` attaches metadata to `say_hello`.
* `enable_openapi=True` is a flag on the Lilya app (we’ll assume your code has been configured to honor that flag and call the generator).

When you later call the function that produces the OpenAPI spec, it will see `/hello` and produce:

```yaml
paths:
   /hello:
      get:
        operationId: say_hello
        summary: Hello endpoint
        responses:
          "200":
            description: Successful response
```

This is just for explanatory and visual purposes, in reality, Lilya produces a JSON specification but this is how it can be represented in YAML.

### Summary, Description, and Tags

```python
{!> ../../../docs_src/openapi/summary_desc_tags.py !}
```

* **`summary`**: A one‐line description that appears in the endpoint list.
* **`description`**: A long‐form Markdown block describing behavior, side effects, etc.
* **`tags`**: Groups operations under “tags” in Swagger UI (e.g. an expandable “users” section).

### Query Parameters

To declare query parameters, use the `Query` class from `lilya.contrib.openapi.params`. It accepts:

* `default`: a default value.
* `description`: human‐readable text.
* `schema`: a minimal JSON‐Schema dict (`{"type": "integer"}`, etc.).
* `required`: a Boolean (by default, `False` if `default` is provided, else `True`).
* `style`: OpenAPI style (e.g. `"form"`, `"deepObject"`, etc.).
* `explode`: OpenAPI explode flag (`True`/`False`).

#### Single Scalar Query

```python
{!> ../../../docs_src/openapi/query.py !}
```

**Resulting OpenAPI parameter**:

  ```yaml
  parameters:
    - name: limit
      in: query
      description: Max items to return
      required: false
      schema:
        type: integer
      default: 10
  ```

#### Array Query

This is how you do an **array** query parameter, which OpenAPI calls “form style”:

```python
{!> ../../../docs_src/openapi/query_array.py !}
```

**Resulting OpenAPI parameter**:

  ```yaml
  parameters:
    - name: tags
      in: query
      description: Filter by multiple tag names
      required: false
      schema:
        type: array
        items:
          type: string
      style: form
      explode: true
      default: []
  ```

#### Deep Object Query (Nested Dictionaries)

```python
{!> ../../../docs_src/openapi/nested.py !}
```

**Resulting OpenAPI parameter**:

  ```yaml
  parameters:
    - name: filter
      in: query
      description: Filter object
      required: false
      schema:
        type: object
        additionalProperties:
          type: string
      style: deepObject
      explode: true
      default: {}
  ```

#### Path vs. Query Name Collision

If your handler signature has a path parameter and you also declare a query with the same name, **the query param is dropped**
from the documentation, since the path‐param takes priority. Example:

```python
{!> ../../../docs_src/openapi/collision.py !}
```

* **`/users/{user_id}`**
* The code will only document:

  ```yaml
  parameters:
    - name: user_id
      in: path
      required: true
      schema: {type: string}
  ```

and **not** list `user_id` again under `in: query`.

!!! Tip
    Although Lilya is smart enough to detect this and avoid collisions, it can happen that sometimes this validation might fail.

    Always use distinct names for path and query parameters to avoid confusion. For example, use `user_id` in the path and `userIdQuery` in the query.

---

### Response Models

Responses are declared via `OpenAPIResponse` from `lilya.contrib.openapi.datastructures`. You map integer status codes to `OpenAPIResponse(...)` instances.

```python
{!> ../../../docs_src/openapi/response_model.py !}
```

1. **`model=Item`**: A Pydantic model class. The generator will:
    1. Produce a JSON Schema under `components.schemas.Item`.
    2. Insert, under `"/items/{item_id}" → get → responses → "200" → content → "application/json"`, a `$ref: "#/components/schemas/Item"`.

2. **`model=ErrorModel`**: Another Pydantic class (e.g. `ErrorModel(detail: str)`). It will appear under `components.schemas.ErrorModel` and be referenced by `400`.
3. **Default Media Type**: If you do not specify `media_type` on the `OpenAPIResponse`, it defaults to `"application/json"`.

#### Array‐of‐Model Syntax

To return an array of a Pydantic model, pass a Python list containing one model:

```python
{!> ../../../docs_src/openapi/response_model_list.py !}
```

* Under the hood, this is equivalent to “an array of `Person`.” The generator will:
    * Generate a `Item` JSON Schema under `components.schemas.Item`.
    * Document the response as:

     ```yaml
     content:
       application/json:
         schema:
           type: array
           items:
             $ref: "#/components/schemas/Item"
     ```

#### Response Description (Default 200)

If you omit `responses` entirely, every handler gets a fallback:

```yaml
200:
  description: Successful response
```

#### Overriding Media Type

If you want to return XML, you can:

```python
{!> ../../../docs_src/openapi/override_media_type.py !}
```

!!! Note
    **Important**: Allowed media types are restricted (e.g. `"application/json"`, `"text/plain"`, `"application/xml"`, etc.)
    the underlying `OpenAPIResponse` will validate against a predefined enum/value.

---

## Organizing Routes: `Path`, `Include`, and Child Apps

Lilya’s routing allows you to compose URLs via:

1. **`Path(path_format, handler, methods=[...], include_in_schema=True)`**
2. **`Include(prefix, routes=[ ... ])`**
3. **`Include(prefix, app=ChildLilya(...))`**

Under the hood, `Include` segments often introduce a catch-all placeholder (e.g. `"{path:path}"`) so that all sub‐URLs are forwarded.
The OpenAPI generator automatically strips those placeholders from intermediate segments so that your documented paths remain clean.

### Path Basics

```python
{!> ../../../docs_src/openapi/path_basics.py !}
```

* **`Path("/health", handler)`** registers the route `GET /health`.
* The generator will document `/` and `/health` as separate entries.
* You can specify alternative HTTP methods:

  ```python
  Path("/items", handler, methods=["GET", "POST"])
  ```

to document both `GET /items` and `POST /items`.

### Single-Level `Include(...)`

```python
{!> ../../../docs_src/openapi/single_level.py !}
```

* Internally, Lilya maps `"/nest/leaf"` to `leaf_handler`.
* When generating OpenAPI, the generator sees `Include("/nest", [Path("/leaf", …)])` and produces a documented path `"/nest/leaf"`.
* Any intermediate placeholder like `"/nest/{path:path}"` is stripped to just `"/nest"`.

### Multi-Level Nesting

You can nest `Include` arbitrarily:

```python
{!> ../../../docs_src/openapi/multi_level.py !}
```

* Documented endpoint: `GET /level1/level2/deep`.
* No placeholders appear, even though Lilya may internally represent the second level as `"/level1/{path}/level2/{path}/deep"`.

### Child Lilya App Mounts

Sometimes you have a separate Lilya app that you want to mount under a prefix:

```python
{!> ../../../docs_src/openapi/child_app.py !}
```

* Internally, `child_app` is mounted at `"/child/{path:path}"`.
* When generating docs, `"/child/{path}"` is stripped to `"/child"`, and the generator recurses into `child_app.routes`.
* Documented endpoints become:

  * `GET /child/hello`
  * `GET /child/bye`

### Removing Internal Placeholders

Whenever a route or child app uses a “typed placeholder” like `"{path:path}"` or `"{rest_of_url:path}"`, it is removed from intermediate segments.
Only the *leaf* path parameters remain visible. For example:

```python
Include("/api", app=child_app)
```

* Lilya’s internal route might be `"/api/{path:path}"`.
* The generator sees `"/api/{path:path}"`, splits on `"/{"`, takes `"/api"`, and recurses.
* Future recursion gets `"/api/hello"`, which stays intact—so you never see `"{path}"` in the final doc.

---

## Generating the OpenAPI Document

Once all your handlers are decorated with `@openapi` and your Lilya app’s `routes` are fully defined, you call a single function commonly named
`get_openapi` to produce a dictionary representing the OpenAPI JSON.

### The OpenAPI configuration

You don't need to do this as internally Lilya does it for you but if you can override the openapi configuration and pass it to Lilya.

```python
{!> ../../../docs_src/openapi/openapi_config.py !}
```

Then you can simply pass the `openapi_config` to Lilya:

```python
{!> ../../../docs_src/openapi/openapi_config_lilya.py !}
```

### The OpenAPIConfig object

The object `OpenAPIConfig` is a simple data structure that holds the configuration for the OpenAPI generation. It includes:

#### OpenAPIConfig Attributes

The `OpenAPIConfig` model encapsulates all settings that control how Lilya generates and serves your OpenAPI documentation. Below is a detailed overview of each attribute, its purpose, type, and default value.

---

##### `title: str | None`

* **Description**: The title that appears in the top-level `info.title` of the OpenAPI JSON and is displayed in Swagger UI, ReDoc, etc.
* **Type**: `str` (nullable)
* **Default**: `"Lilya"`
* **Usage**:

  * In the generated JSON,

    ```json
    "info": {
      "title": "Lilya",
      …
    }
    ```
  * When you open Swagger UI at `/docs/swagger`, the browser tab and header show “Lilya - Swagger UI”.

---

##### `version: str | None`

* **Description**: The version string for your API documentation, mapped to `info.version`. By default, it uses Lilya’s own `__version__`.
* **Type**: `str` (nullable)
* **Default**: `__version__` (e.g. `"0.1.0"`, depending on Lilya’s installed version)
* **Usage**:

  * Appears in the OpenAPI JSON:

    ```json
    "info": {
      "version": "0.1.0",
      …
    }
    ```
  * In UI footers (Swagger/ReDoc) to indicate which revision of your API is documented.

---

##### `summary: str | None`

* **Description**: A short, one-line summary for `info.summary`, giving a very brief overview of the entire application/API.
* **Type**: `str` (nullable)
* **Default**: `"Lilya application"`
* **Usage**:

  * In the JSON:

    ```json
    "info": {
      "summary": "Lilya application",
      …
    }
    ```
  * Displayed immediately under the title in many OpenAPI UIs.

---

##### `description: str | None`

* **Description**: A longer, more detailed description for `info.description`. This field supports Markdown formatting and can cover architecture, usage notes, or any high‐level explanation.
* **Type**: `str` (nullable)
* **Default**: `"Yet another framework/toolkit that delivers."`
* **Usage**:

  * Renders in the expanded “Info” panel of Swagger UI or as introductory text in ReDoc.

---

##### `contact: dict[str, str|Any] | None`

* **Description**: Contact information for the API owner/maintainer. Must follow OpenAPI’s contact object schema (keys like `name`, `url`, `email`).
* **Type**:

  ```python
  {
      "name": str,
      "url": str,
      "email": str
  }  # or None
  ```
* **Default**:

  ```python
  {"name": "Lilya", "url": "https://lilya.dev", "email": "admin@myapp.com"}
  ```
* **Usage**:

  * In the JSON:

    ```json
    "info": {
      "contact": {
        "name": "Lilya",
        "url": "https://lilya.dev",
        "email": "admin@myapp.com"
      },
      …
    }
    ```
  * In the UI, appears under “Contact” with clickable email and URL.

---

##### `terms_of_service: AnyUrl | None`

* **Description**: A URL pointing to your API’s Terms of Service. Placed in `info.termsOfService`.
* **Type**: `AnyUrl` (Pydantic‐validated URL) or `None`
* **Default**: `None`
* **Usage**:

  * If set, appears in the JSON as

    ```json
    "info": {
      "termsOfService": "https://example.com/terms",
      …
    }
    ```
  * Renders in UIs as a clickable “Terms of Service” link.

---

##### `license: dict[str, str|Any] | None`

* **Description**: License information for the API, following OpenAPI’s license object schema (e.g. `{"name": "MIT", "url": "https://opensource.org/licenses/MIT"}`).
* **Type**:

  ```python
  {
      "name": str,
      "url": str
  }  # or None
  ```
* **Default**: `None`
* **Usage**:

  * In the JSON:

    ```json
    "info": {
      "license": { "name": "MIT", "url": "https://opensource.org/licenses/MIT" },
      …
    }
    ```
  * Displays as “License” in Swagger UI/ReDoc.

---

##### `security: Any | None`

* **Description**: Global security requirements for the API, following OpenAPI’s security requirement object format. For example, to require a Bearer token on every endpoint:

  ```python
  [{"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}]
  ```
* **Type**: Any valid OpenAPI‐compliant security requirement or `None`
* **Default**: `None`
* **Usage**:

  * Included at the root of the JSON as

    ```json
    "securitySchemes": [{ "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"} }]
    ```
  * Most UI tools show a “lock” icon and allow users to authorize once for all endpoints.

---

##### `servers: list[dict[str, str|Any]] | None`

* **Description**: An array of server objects (as defined by OpenAPI). Each object must have at least a `"url"` key, and may include `"description"`.
* **Type**:

  ```python
  [
    {"url": str, "description": str (optional)},
    …
  ]  # or None
  ```
* **Default**: `[{"url": "/"}]`
* **Usage**:

  * In the JSON:

    ```json
    "servers": [
      {"url": "/"},
      {"url": "https://api.example.com", "description": "Production"}
    ]
    ```
  * Swagger UI/ReDoc display a server‐selection dropdown if multiple entries exist.

---

##### `tags: list[str] | None`

* **Description**: A list of tags (as simple strings) that can be used to group and order endpoints in the docs.
* **Type**: `List[str]` or `None`
* **Default**: `None`
* **Usage**:

  * In the JSON:

    ```json
    "tags": [
      { "name": "items" },
      { "name": "users" }
    ]
    ```
  * Each endpoint’s metadata can specify one or more of these tags; UI groups ops under each tag.

---

##### `openapi_version: str | None`

* **Description**: The OpenAPI specification version to declare at the top of the JSON (for example, `"3.1.0"` or `"3.0.0"`).
* **Type**: `str` (nullable)
* **Default**: `"3.1.0"`
* **Usage**:

  * In the JSON:

    ```json
    {
      "openapi": "3.1.0",
      …
    }
    ```
  * Some tools may require a specific major/minor version; adjust here if necessary.

---

##### `openapi_url: str | None`

* **Description**: The relative URL path at which the raw OpenAPI JSON (or YAML) is served.
* **Type**: `str` (nullable)
* **Default**: `"/openapi.json"`
* **Usage**:

  * Lilya registers a hidden route (not included in `paths`) at this URL.
  * Example: A request to `GET /openapi.json` returns the JSON spec with

    ```python
    return JSONResponse(self.openapi(app))
    ```
  * If you set `openapi_url=None`, Lilya will not create that route, and you must supply your own.

---

##### `root_path_in_servers: bool`

* **Description**: When `True`, Lilya automatically prepends its `root_path` (if any) to the server list at runtime. This is useful when deploying behind proxies or mounting under a sub‐URL.
* **Type**: `bool`
* **Default**: `True`
* **Usage**:

  * Lilya checks `request.scope["root_path"]`, and if it’s not already in `servers`, it inserts it at index 0.
  * Ensures that UIs will use the correct base URL even if you mount the app under `/myapp`.

---

##### `docs_url: str | None`

* **Description**: The relative path where Swagger UI is exposed.
* **Type**: `str` (nullable)
* **Default**: `"/docs/swagger"`
* **Usage**:

  * Lilya creates a hidden route at `GET /docs/swagger` that returns HTML rendering of Swagger UI.
  * You can change to `"/api/docs"` if you prefer that URL.
  * If you set `docs_url=None`, Swagger UI is not served.

---

##### `redoc_url: str | None`

* **Description**: The relative path where ReDoc is exposed.
* **Type**: `str` (nullable)
* **Default**: `"/docs/redoc"`
* **Usage**:

  * Lilya registers `GET /docs/redoc` to render ReDoc with the spec URL.
  * If `redoc_url=None`, ReDoc is not served.

---

##### `swagger_ui_oauth2_redirect_url: str | None`

* **Description**: The relative path for the OAuth2 redirect page used by Swagger’s “Authorize” button.
* **Type**: `str` (nullable)
* **Default**: `"/docs/oauth2-redirect"`
* **Usage**:

  * If present, Lilya creates `GET /docs/oauth2-redirect` returning the HTML snippet required by Swagger UI to perform OAuth2 flows.
  * If `None`, OAuth2 redirect support is disabled in Swagger.

---

##### `redoc_js_url: str | None`

* **Description**: The external URL to the ReDoc JavaScript bundle used when rendering ReDoc.
* **Type**: `str` (nullable)
* **Default**: `"https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"`
* **Usage**:

  * Injected into the ReDoc HTML `<script src="…">`.
  * Change this if you want a local copy or a different CDN version.

---

##### `redoc_favicon_url: str | None`

* **Description**: The URL for the favicon displayed in ReDoc.
* **Type**: `str` (nullable)
* **Default**: `"https://www.lilya.dev/statics/images/favicon.ico"`
* **Usage**:

  * Rendered in the ReDoc `<head>` as:

    ```html
    <link rel="icon" href="https://www.lilya.dev/statics/images/favicon.ico" />
    ```
  * Change to your own favicon if desired.

---

##### `swagger_ui_init_oauth: dict[str, Any] | None`

* **Description**: A dictionary of OAuth2 configuration parameters that are passed to Swagger UI’s `initOAuth(...)` call.
* **Type**: `dict` or `None`
* **Default**: `None`
* **Usage**:

  * When Swagger UI loads, it executes:

    ```js
    ui.initOAuth({ /* your dict here */ });
    ```
  * Useful for customizing OAuth2 client IDs, scopes, and PKCE options.

---

##### `swagger_ui_parameters: dict[str, Any] | None`

* **Description**: A dictionary of additional Swagger UI configuration options (e.g. `deepLinking`, `displayRequestDuration`, `filter`, etc.).
* **Type**: `dict` or `None`
* **Default**: `None`
* **Usage**:

  * Injected into the `SwaggerUIBundle` constructor, e.g.:

    ```js
    const ui = SwaggerUIBundle({
      url: openapiUrl,
      …,
      deepLinking: true,
      filter: true,
      …
      …this.swagger_ui_parameters
    });
    ```
  * Customize how Swagger UI behaves (whether to show “Try it out,” theme, layout, etc.).

---

##### `swagger_js_url: str | None`

* **Description**: The URL to the Swagger UI JavaScript bundle.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.4/swagger-ui-bundle.min.js
  ```
* **Usage**:

  * Included via `<script src="…"></script>` in the Swagger UI HTML.
  * Change if you host a local copy or need a different version.

---

##### `swagger_css_url: str | None`

* **Description**: The URL to the Swagger UI CSS file.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.4/swagger-ui.min.css
  ```
* **Usage**:

  * Injected via `<link rel="stylesheet" href="…">` in the Swagger UI HTML.
  * Change to a local copy or a different theme if desired.

---

##### `swagger_favicon_url: str | None`

* **Description**: The URL for the favicon used in Swagger UI.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://lilya.dev/statics/images/favicon.ico
  ```
* **Usage**:

  * Included in the HTML `<head>` for Swagger:

    ```html
    <link rel="icon" href="https://lilya.dev/statics/images/favicon.ico" />
    ```
  * Change this to your own brand’s favicon.

---

##### `with_google_fonts: bool`

* **Description**: If `True`, ReDoc HTML will load Google Fonts. If `False`, it omits the `<link>` to Google Fonts (saving external requests).
* **Type**: `bool`
* **Default**: `True`
* **Usage**:

  * When serving ReDoc, Lilya includes:

    ```html
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    ```
  * Setting this to `False` skips that line.

---

##### `stoplight_js_url: str | None`

* **Description**: The URL to the Stoplight Elements JavaScript bundle.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://unpkg.com/@stoplight/elements/web-components.min.js
  ```
* **Usage**:

  * Included when serving Stoplight under `stoplight_url`.
  * Change if you host locally or need a newer/older version.

---

##### `stoplight_css_url: str | None`

* **Description**: The URL to the Stoplight Elements CSS file.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://unpkg.com/@stoplight/elements/styles.min.css
  ```
* **Usage**:

  * Included via `<link rel="stylesheet" href="…">` in the Stoplight HTML.
  * Change to a local copy or a different theme as needed.

---

##### `stoplight_url: str | None`

* **Description**: The relative path where Stoplight Elements UI is exposed.
* **Type**: `str` (nullable)
* **Default**: `"/docs/elements"`
* **Usage**:

  * Lilya registers a hidden route at `GET /docs/elements` that renders Stoplight Elements with the API spec.
  * Set to `None` to disable Stoplight.

---

##### `stoplight_favicon_url: str | None`

* **Description**: The URL for the favicon used in Stoplight Elements docs.
* **Type**: `str` (nullable)
* **Default**: `None`
* **Usage**:

  * If provided, included in the Stoplight HTML `<head>`.
  * If omitted, Stoplight uses its default icon.

---

##### `rapidoc_url: str | None`

* **Description**: The relative path where RapiDoc UI is exposed.
* **Type**: `str` (nullable)
* **Default**: `"/docs/rapidoc"`
* **Usage**:

  * Lilya registers `GET /docs/rapidoc` for RapiDoc.
  * If set to `None`, RapiDoc is not available.

---

##### `rapidoc_js_url: str | None`

* **Description**: The URL to the RapiDoc JavaScript bundle.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://unpkg.com/rapidoc@9.3.4/dist/rapidoc-min.js
  ```
* **Usage**:

  * Included via `<script src="…"></script>` in the RapiDoc HTML.
  * Change if you need a local copy or specific version.

---

##### `rapidoc_favicon_url: str | None`

* **Description**: The URL for the favicon used in the RapiDoc UI.
* **Type**: `str` (nullable)
* **Default**:

  ```
  https://esmerald.dev/statics/images/favicon.ico
  ```
* **Usage**:

  * Injected in the RapiDoc HTML `<head>`.
  * Replace with your own icon to match your brand.

---

##### `webhooks: Sequence[Any] | None`

* **Description**: A list of webhook definitions, following OpenAPI’s “webhooks” object schema. Each item can be a dictionary or a Pydantic‐validated webhook schema.
* **Type**: `Sequence[Any]` or `None`
* **Default**: `None`
* **Usage**:

  * If provided, Lilya includes a top‐level `"webhooks": { … }` section in the OpenAPI JSON.
  * UI tools that support webhooks will list them after the regular paths.

---

## How Lilya Uses These Attributes

When you pass an instance of `OpenAPIConfig` to your `Lilya` app:

```python
{!> ../../../docs_src/openapi/config_usage.py !}
```

1. **On startup**, Lilya detects `openapi_config` and calls `config.enable(app)`.
2. **`config.enable(app)`** registers hidden routes (not included in `paths`) for:
    * The raw OpenAPI JSON at `config.openapi_url` (e.g. `GET /api/schema`).
    * Swagger UI at `config.docs_url` (e.g. `GET /docs/swaggerui`).
    * Swagger OAuth2 redirect at `config.swagger_ui_oauth2_redirect_url` (if set).
    * ReDoc at `config.redoc_url`.
    * Stoplight at `config.stoplight_url`.
    * RapiDoc at `config.rapidoc_url`.
    * Each of these handlers uses the corresponding HTML helper (e.g. `get_swagger_ui_html`) and injects your chosen JS/CSS URLs, favicon URLs, and initialization parameters.
3. **The raw JSON route** calls `config.openapi(app)` under the hood, which in turn calls `get_openapi(...)`
using your attributes (`title`, `version`, `tags`, `servers`, etc.) to produce a fresh OpenAPI dictionary. That dictionary is stored in `app.openapi_schema`
for other tools to access.

Because every attribute in `OpenAPIConfig` has a default, you can override just the ones you need. Any field you do not set remains at its default.
If you do not supply an `OpenAPIConfig` at all, Lilya constructs a default one behind the scenes.

---

## Examples: From Lilya Code to OpenAPI JSON

Below are progressively more complex examples showing how Lilya routes, decorators, and nested includes translate into documented paths.

### Minimal App with One Route

```python
{!> ../../../docs_src/openapi/examples/minimal.py !}
```
No `parameters`, no `components.schemas` (no models used).

### App with Query Parameters and Response Models

```python
{!> ../../../docs_src/openapi/examples/request_query.py !}
```

### Nested Includes and Child Apps

#### Single-Level Include

```python
{!> ../../../docs_src/openapi/examples/nest_includes_and_child.py !}
```

Notice how the internal placeholder `"{path}"` (if any) is stripped—only `/api/leaf` appears.

#### Two-Level Include

```python
{!> ../../../docs_src/openapi/examples/two_level_include.py !}
```

#### Child Lilya App

```python
{!> ../../../docs_src/openapi/examples/child_app.py !}
```

###  Combining Everything: A Full‐Featured Example

```python
{!> ../../../docs_src/openapi/examples/all_in.py !}
```

* Notice how `/users/{user_id}/items` and `/account/profile` both end up calling `list_user_items`, but their parameters differ:
    * The first has `user_id` as a path param.
    * The second omits the path param because `/account/profile` had no `{user_id}` in its prefix.
* In the “extra” include, the placeholder appears after `/users`, hence `/users/extra/{user_id}/extra-info`.

---

## Edge Cases & Common Pitfalls

### Name Collisions: Path vs. Query

If you declare a query parameter whose name is identical to a path variable, the query parameter is silently dropped from the documentation. For example:

```python
{!> ../../../docs_src/openapi/examples/collisions.py !}
```

* Only the path parameter “id” appears in the docs. The query “id” is removed.

!!! Tip
    **Recommendation**: Always choose distinct names (e.g., `{user_id}` vs. `?userIdQuery=...`) to avoid confusion and errors.

### Typed Catch-All Placeholders (`{path:path}`)

Lilya automatically inserts a catch-all path parameter for certain nested includes or child-app mounts. For instance:

```python
child_app = Lilya(routes=[Path("/x", handler)])
app = Lilya(routes=[Include("/child", app=child_app)])
```

Internally, Lilya’s mount might be `"/child/{path:path}/x"`. The OpenAPI generator strips out `"/{path:path}"` so that you only see
`"/child/x"` in the final documentation.

!!! Note
    **Important**: If you explicitly want to document a catch-all like `"/resources/{rest_of_url:path}"`, that design is not directly
    supported—any typed placeholder in a non-leaf segment is stripped. Only leaf-level placeholders (e.g. `"/resources/{id}"`) remain documented.

### Arrays of Models vs. Single Models

#### Single Model: `OpenAPIResponse(model=User, description="User info")`
  → Under `components.schemas.User`. Response:

  ```yaml
  schema:
    $ref: "#/components/schemas/User"
  ```

#### Array of Models: `OpenAPIResponse(model=[User], description="List of users")`
  → Under `components.schemas.User`. Response:

  ```yaml
  schema:
    type: array
    items:
      $ref: "#/components/schemas/User"
  ```

!!! Warning
    Do **not** pass `model=list[User]` directly to the decorator; if you do, you must convert it to `[User]` so the wrapper can unwrap it properly.
    The decorator’s logic will detect a Python `list` or `tuple` and take the first element as the inner Pydantic model.

### Exclude a Route from Documentation

If you set `include_in_schema=False` on a `Path`, that route is omitted entirely from `paths`.

```python
{!> ../../../docs_src/openapi/examples/include_in_schema.py !}
```

* Only `/visible` appears in the final `spec["paths"]`.

### Unsupported Media Types

When specifying `media_type` in `OpenAPIResponse`, you must choose from a restricted set
(e.g. `"application/json"`, `"text/plain"`, `"application/xml"`, `"application/octet-stream"`, `"multipart/form-data"`, etc.).

If you pass an unsupported string, you will get a validation error. Check the underlying enum (in Pydantic or the OpenAPI datastructures) for the full list.
