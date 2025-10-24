---
hide:
  - navigation
---

# Release Notes

## 0.22.7

### Changed

- Improved the internals of the shell when loading.

### Fixed

- Encoders were overriding values stripping forbidden values. Evaluation is now done on the whole json.

## 0.22.6

### Fixed

- Fix 502 Gateway timeout when using `EventStreamResponse` with long-lived connections.

## 0.22.5

### Added

- Support for [dependency overrides](./dependencies.md#dependency-overrides). This allows you to override dependencies globally in the application
or in specific includes. This is particularly useful for testing and mocking dependencies.

### Changed

- `EnvironLoader` now support native YAML files.
- [Environments](./environments.md) documentation section with examples and usage.

### Fixed

- Fixed `EventStreamResponse` error message to display in seconds and not milliseconds.

## 0.22.4

This was missed from the 0.22.3 release.

### Fixed

- Fixed `EventStreamResponse` when it was not establishing the connection properly.

## 0.22.3

### Added

- `runserver_theme` to `Lilya` settings and `runserver` directive. This allows you to customise the theme of the
`lilya runserver` command.

### Fixed

- Regression in runserver with a path provided.

## 0.22.2

### Added

- Support for multiple cookie headers in the `Request` object. This follows the [RFC 7540](https://datatracker.ietf.org/doc/html/rfc7540).

### Changed

- Core implementation for EventStreamResponse to support multiple headers and parameters.

## 0.22.1

### Changed

- Lilya `requires` now accepts a parameter for custom connection name checking and removes the enforcing of
the connection name to be None.
- Extend the `authenticate` signature with extra kwargs for `lilay.authentication.AuthenticationBackend`.

### Fixed

- Documentation typos.

## 0.22.0

### Added

- New [Lifecycle](./lifecycle.md) system allowing to create global and app level lifecycle hooks. With more explanatory
documentation.
- **Dependency Scopes** — Introduced a flexible scoping system for dependency lifetimes.
    - `Scope.REQUEST`: Default per-request lifetime.
    - `Scope.APP`: Application-wide shared dependencies.
    - `Scope.GLOBAL`: Process-level shared instances.
- New security [SignedURL](./contrib/security/signed-urls.md) utility for generating and verifying time-limited signed URLs.
- New [SSEChannel](./contrib/sse.md) class for creating in-memory Server-Sent Events channels with pub/sub support.

### New Responses

- [CSVResponse](./responses.md#csvresponse) as a new available response for CSV files directly in the `lilya.responses`.
- [YAMLResponse](./responses.md#yamlresponse) as a new available response for YAML files directly in the `lilya.responses`.
- [XMLResponse](./responses.md#xmlresponse) as a new available response for XML files directly in the `lilya.responses`.
- [MessagePackResponse](./responses.md#messagepackresponse) as a new available response for MessagePack files directly in the `lilya.responses`.
- [NDJSONResponse](./responses.md#ndjsonresponse) as a new available response for Newline Delimited JSON files directly in the `lilya.responses`.
- [ImageResponse](./responses.md#imageresponse) as a new available response for images directly in the `lilya.responses`.
- `TextResponse` as a new available response for plain text files directly in the `lilya.responses`.
- [EventStreamResponse](./responses.md#eventstreamresponse) as a new available response for Server-Sent Events directly in the `lilya.responses`.

### Fixed

- CompactSerializer was not overriding kwargs properly.

## 0.21.1

### Added

- **OpenTelemetry integration** under `lilya.contrib.opentelemetry`:
  - Introduced `OpenTelemetryMiddleware` for automatic request tracing.
    - Creates one `SERVER` span per HTTP request.
    - Records standard HTTP attributes (`method`, `path`, `status`, `client.address`, `url.query`, etc.).
    - Captures exceptions and marks spans with `StatusCode.ERROR`.
    - Handles parent context extraction from inbound headers for trace propagation.
  - Added `setup_tracing(config: OpenTelemetryConfig | None)` helper.
    - Initializes a global `TracerProvider` with a `BatchSpanProcessor`.
    - Automatically selects between `ConsoleSpanExporter`, `OTLP/gRPC`, and `OTLP/HTTP` exporters.
    - Safe to call multiple times (idempotent).
  - Added `OpenTelemetryConfig` dataclass for configuration.
    - Supports fields:
      - `service_name`: logical name reported to telemetry backends.
      - `exporter`: `"otlp"` or `"console"`.
      - `otlp_endpoint`: e.g. `"http://localhost:4317"` or `"http://collector:4318"`.
      - `otlp_insecure`: disable TLS verification for gRPC exporters.
      - `sampler`: `"parentbased_always_on"`, `"always_on"`, or `"always_off"`.
  - Added `get_tracer_provider()` utility to retrieve the active `TracerProvider`.
- **Async testing utilities**:
    - Introduced [AsyncTestClient](./test-client.md#the-async-test-client) and [create_async_client()](./test-client.md#context-manager-create_async_client) to allow fully asynchronous testing of Lilya apps.
    - Both support full middleware stacks, including `OpenTelemetryMiddleware`.
    - Enables concurrent request tests and real async span creation with in-memory exporters.
- Contrib Shortcuts:
  - New [abort](./contrib/shortcuts/abort.md) function to raise HTTP exceptions.
  - New [responses shorcuts](./contrib/shortcuts/responses.md) including:
    - `send_json()`: send JSON responses with proper headers.
    - `json_error()`: send JSON error responses with status codes.
    - `stream()`: stream response content from async generators.
    - `empty()`: return empty 204 No Content responses.
    - `redirect()`: send HTTP redirects with proper status codes and headers.
    - `forbidden()`: send 403 Forbidden responses.
    - `not_found()`: send 404 Not Found responses.
    - `unauthorized()`: send 401 Unauthorized responses.

### Changed

- `redirect` now is in `lilya.contrib.responses.shortcuts`.

### Fixed

- `send_file` now correctly sets `Content-Disposition` headers for file downloads.
- Late binding in the `make_response`.

## 0.21.0

### Added

- Python 3.14 support.

## 0.20.10

### Fixed

- Validation `upper()` was not being applied properly in the csrf token.

## 0.20.9

This was supposed to go in the version 0.20.8 and it was forgotten.

### Added

- `__exclude_from_openapi__` Added to the base controller allowing the exclusion from the BaseTemplates.

### Changed

- Lilya create project default was still using an old version of the generator.

### Fixed

- OpenAPI documentation was not excluding templating system and statics.

## 0.20.8

### Added

- `itsdangerous` to requirements `all` and `standard`.

### Changed

- `@directive(display_in_cli=True)` discovery improved by showing errors and not throw directly
an exception.
- Update minimum Sayer version to 0.6.0.
- Custom directives under `@directive` are now displayed in a "Custom directives" group.

## 0.20.7

### Added

- `csrf_token_name` as new parameter in the Lilya settings. This will allow you to globally set the name of the
`csrf` token when using CSRFMiddleware.
- `csrf_enabled` flag to `TemplateController`. This will automatically inject the `csrf` token in the context of the templates.
- `csrf_token_form_name` to `TemplateController`. This defaults to `csrf_token` and corresponds to the name of the variable
that is injected in the context of the template for the CSRF token when `csrf_enabled`.
- Support for `@directive` to be display when calling `lilya` client.
- [display_in_cli](./directives/directive-decorator.md#the-display_in_cli-option) to `@directive`.

### Changed

- Make `response` optional in the `get_or_set_csrf_token`.

### Removed

- Wrong example for the CSRF token in the [security with CSRF](./contrib/security/csrf.md).

## 0.20.6

### Added

- [Relay](./contrib/proxy/relay.md). This allows to create objects that are ASGI compatible and upstream services within your Lilya application.
- **WebSocket proxying**: Added full support for bidirectional WS proxying (text + binary frames).
- **Retry & backoff**: Configurable retry logic with exponential backoff on retryable statuses/exceptions.
- **Timeout mapping**: Upstream timeouts now map to `504 Gateway Timeout`.
- **Header policies**: Added support for allow-list mode (`allow_request_headers`, `allow_response_headers`) in addition to drop-lists.
- **Structured logging**: Proxy events (`upstream_error`, `upstream_timeout`, `upstream_retryable_error`) now emit consistent log messages for observability.
- Support for [CSRFMiddleware](./middleware.md#csrfmiddleware) to understand the HTML forms allowing also custom fields.
- New [HTML](./responses.md#html) response as an alternative to `HTMLResponse`.
- New documentation section for [security with CSRF](./contrib/security/csrf.md).

### Changed

- Added `python-multipart` as part of the `all` and `standard` Lilya packages.
- Replaced `python-multipart` with a fully native multipart, urlencoded, and octet-stream form parser.
- Improved RFC 5987 parameter decoding for proper handling of UTF-8 filenames and headers.
- `AuthenticationError` exception is now located in `lilya.exceptions`.

## 0.20.5

This was a change for the newer sayer 0.5.1 that affects the client.

### Changed

- Allow minimum Sayer to be 0.5.1.
- Lilya cli now loses the `name` argument. This is now handled directly by the newest Sayer that
was internal refactored for the `@callback`.

## 0.20.4

### Changed

- Update sayer dependency version to 0.5.0 and pin it.

## 0.20.3

### Added

- `ValidationError` added to `lilya.exceptions`.
- Introduced [lilya.contrib.mail](./contrib/mail.md) providing a full-featured, async-first email framework.
- Includes a high-level `Mailer` API for sending single, multiple, and templated messages.
- Supports multipart messages (text + HTML), custom headers, attachments (in-memory or files), and metadata.
* CLI integration, `lilya mail sendtest`, for sending quick test emails via console backend.

#### Built-in Backends

- **SMTPBackend**: Async-friendly with connection pooling and TLS/authentication.
- **ConsoleBackend**: Writes messages to stdout for debugging.
- **FileBackend**: Saves emails as `.eml` files for inspection or archiving.
- **InMemoryBackend**: Stores emails in memory for development or testing scenarios.

#### Email Templates

- Added `TemplateRenderer` with Jinja2 integration.
- `send_template` generates HTML + auto text fallbacks.
- Supports separate text/HTML templates and contextual rendering.

#### Application Integration

* New `setup_mail(app, backend, template_dir, attach_lifecycle=True)` utility attaches a `Mailer` to `app.state.mailer`.
* Automatically opens/closes backend connections via startup/shutdown hooks.

#### Exception Hierarchy

* `MailError`: Base exception for all mail errors.
* `BackendNotConfigured`: Raised when no backend or template renderer is configured.
* `InvalidMessage`: Raised when an `EmailMessage` is incomplete or malformed.

## 0.20.2

### Added

- `is_json` and `is_form` properties for `Request`.
- Support for automatic body inference from forms (application/x-www-form-urlencoded and multipart/form-data), in addition to JSON.
- Complex types with collections, lists, sets, dicts supported by `infer_body` as True.
- File uploads (UploadFile and list[UploadFile]) are now seamlessly supported in body inference.
- Introduced dotted key expansion `(user.name=lilya)` and bracket list notation `(items[0].sku=test)` to express nested objects and lists in form submissions.
- New [FormController](./templates.md#formcontroller) class based view template that is agnostic to any validation library.

### Changed

- Inferred body to allow the form request to be parsed properly.
- Improved typed structuring: collections like list[Item], tuple[Item, ...], dict[str, Item], and sets are now properly inferred and converted into typed objects.

## 0.20.1

### Added

- New [send_file](./contrib/files/send-file.md) to **contrib**.
- New [jsonify](./contrib/files/jsonify.md) to **contrib**.

### Changed

- Morph path argument into path option and expose it for all commands.
- Add `wrap_dependency` for inherited Controller dependencies.

### Fixed

- Properly detect wrapped Lilya instances.
- Fix crash in show-urls.
- Fix double initialization of app in runserver.

### Breaking

- lilya runserver loses its path argument. You can specify it via `lilya --path foo runserver`.

## 0.20.0

### Added

- New request‑agnostic **Depends** for DI anywhere (sync/async, nested deps, overrides, per‑instance caching).
- Added **@inject** decorator to auto‑resolve `Depends` on call. This preserves signature and honors explicit args.

#### Example

```python
from lilya.dependencies import Depends, inject


def get_db():
    session = Sessionlocal()
    try:
        yield session
    finally:
        session.close()


@inject
def get_db_session(db = Depends(get_db)) -> Any:
    return db
```

## 0.19.8

### Added

- Allow using `str` as `handler` param for the `Path` and `WebsocketPath` as alternative.

### Changed

- `RedirectResponse` default from 307 to `HTTP_303_SEE_OTHER`.

### Fixed

- Runserver when no autodiscovery was enabled.
- Initial settings was not initialising properly in the constructor.
- Edgy template was being wrongly renamed.

## 0.19.7

### Added

- Compact json for the serializers.

### Fixed

- `Query` parsing was overriding the default.

### Changed

- `Encoders` use the native `lilya.serializers.serializer` object instead of direct `json`.

## 0.19.6

### Added

- `--version` attribute when running `createapp` directive allowing to generate a versioned scaffold.
- `--location` attribute when using `createapp` and `createproject` directive allowing to specify the location to be created.
- `--edgy` attribute to `createproject` allowing the generation of project scaffolds integrating Edgy ORM.
- `exception` method to logging protocol.
- `wrap_dependency` internal that will create a `Provide` in case a dependency is passed and no `Provide` is provided.
- Add `Jinja2Templates` as alias to `Jinja2Template`.
- New dynamic, native and fast custom [serializers](./serializers.md).

### Changed

- To make Lilya cleaner in the installation we have now separated the installation. The [Lilya native client](./lilya-cli.md)
requires some additional packages and not everyone requires this or even desires but for those already using, the change is simple.

#### Before

```shell
$ pip install lilya
```

#### After

```shell
$ pip install lilya[standard]
```

This brings the current behaviour of Lilya prior to version 0.19.6 and nothing changes.

## 0.19.5

### Fixed

- Allow string representation of bool in type check

## 0.19.4

### Added

- Support for automatic cast call for a function is a function is provided to cast in the `loader` of the [Environment](./environments.md).
- `UUIDEncoder` as a native for parsing `UUID` types.
- `TimedeltaEncoder` as native encoder.

### Fixed

- Fixed `@cache` when decorating Class controllers and function controllers.
- Permissions were not properly applied on `Controller` type objects.
- Permissions protocol to check for the `__is_contoller__`.
- Documentation references.
- `Query` was not casting properly boolean values.

## 0.19.3

- Permission call order was reversed when called from within an Include, Path, Websocket and internal routing.

## 0.19.2

### Fixed

- Nested dependencies where checking values that were not in the signature of the dependency itself.

## 0.19.1

### Changed

- Root path for auto detection behind reverse proxies.

### Fixed

- Typo in the error for the security.
- Servers for `openapi` were not being detected automatically.

## 0.19.0

### Added

- Contrib security. This contrib is entirely optional and you don't need to use it but is served as an alternative
to allow you to use Lilya security out of the box.

### Fixed

- Nested dependencies that require internal parameters.
- Internals and refactor the OpenAPI spec to match the missing internals.

### Changed

- Refactor the `@openapi` generator for security and authorization.

## 0.18.3

### Added

- Lilya being agnostic to everything still has a contrib to integrate with the whole ecosystem so a native [AsyncZ](https://asyncz.dymmond.com)
was added to support that same integration in a clean fashion.
- New `Contrib` section in the documentation to make it clear the separation of concerns.

## 0.18.2

### Added

- Added support for `Query`  parameter markers.
    * Implemented `alias` support for query parameters to map custom keys.
    * Introduced `cast` field in `Query` for runtime type coercion with validation.
    * Improved error handling for missing and invalid query parameter types.

- Introduced `Header` and `Cookie` parameter markers with `value`, `required`, and `cast` support.
- Expanded documentation into a comprehensive “Request Parameters” guide covering declaration, options, and real-world examples for all three types.

## 0.18.1

### Changed

- Update directives to reflect the new settings.

### Fixed

- Cache dependency on `json` native library.

## 0.18.0

### Added

- Support for native [cache](./caching.md) with default to `InMemory`.
- Add support for relative urls from the `URL` datastructure.
- Support for OpenAPI on Controllers by applying internal identity descriptors.

### Changed

In the past, Lilya was using `dataclass` to manage all the settings but we found out that can be a bit combersome for a lot
of people that are more used to slighly cleaner interfaces and therefore, the internal API was updated to stop using `@dataclass` and
use directly a typed `Settings` object.

- Replace `Settings` to stop using `@dataclass` and start using direct objects instead.

**Example before**

```python
from dataclasses import dataclass, field
from lilya.conf.global_settings import Settings


@dataclass
class MyCustomSettings(Settings):
    hosts: list[str] = field(default_factory=lambda: ["example.com"])
```

**Example after**

```python
from lilya.conf.global_settings import Settings


class MyCustomSettings(Settings):
    hosts: list[str] = ["example.com"]
```

This makes the code cleaner and readable.

- Apply AnyIO to `DataUpload` instead of using BinaryIO.

## 0.17.1

### Changed

* **Dual‑mode support in run_sync:** Now accepts either an async function with args or a standalone coroutine object.
* **Input normalization:** Uses `inspect` to detect and wrap calls into a zero‑argument coroutine factory.
* **Seamless execution:** Drives work on the main thread via `anyio.run`,
with a clean fallback to `ThreadPoolExecutor` if an event loop is active.
* **Error clarity:** Raises a precise `TypeError` when the argument is neither a coroutine function nor object.
* **Simplified API:** Eliminates nested lambdas by centralizing logic into a single `wrapper_fn`
passed to `anyio.run`.

## 0.17.0

### Added

- Missing validation that was supposed to go on the version 0.16.10 and it was not pushed.

### Changed

- Mark `http_exception` in the `Exception` as `async` to avoid thread creation.
- Replace `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction`.
- Replace `asyncio` in `run_sync` with anyio.
- Refactor `run_sync` from `lilya.compat`.

## 0.16.10

### Fixed

- `infer_body` with complex dependencies and path params evaluation when `infer_body=True`

## 0.16.9

### Changed

- Unify dependency injection logic for both Controller and handlers.
- Unify logic for body inferring for Controller and handlers.

## 0.16.8

### Added

- Add support for multi-byterange requests and responses.
- Add retro-compatibility for `path_for` with an alias `url_for`. This allows easier integration with other libraries
that use `url_for` as the method to generate URLs.

### Changed

- Add `lru_cache` to some of the methods that are used to generate URLs. This allows for better performance
when generating URLs that are frequently used.
- **Automatic Generator Unwrapping**: `Provide` and `async_resolve_dependencies` now detect both sync and async generator dependencies,
advance them to yield the real return value, and inject that into handlers.

## 0.16.7

!!! Note
    There was a part of the commit that was not properly pushed and this could cause inconsistencies and therefore
    a quick small release was done.

### Changed

- Dependencies with `infer_body` consistency check.

## 0.16.6

### Added

- Lilya `run` directive now injects the `g` global context for usage in the directives in offline mode.
- Support for http ranges (bytes).
- Support if-range header.
- **Added fallback dependency injection**: Handlers can now receive dependencies even without explicitly using `Provides()`,
as long as they are defined in the app or route.
- **Improved optional injection logic**: Dependencies declared with `Provides()` are treated as required, while others are injected only if available—ensuring flexibility and safety.
- **Unified behavior across HTTP and WebSocket handlers**: Dependency resolution logic now consistently supports both explicit and fallback injection in all handler types.

### Changed

- Don't execute stream or analyze file for options for FileResponse, StreamingResponse. It is certainly unwanted and expensive.
- Don't execute background tasks for options and head. This is certainly unwanted.
- Add `allow_range_requests` parameter to `FileResponse` for allowing to disable http range serving.
- Deprecate the undocumented `method` parameter. It has no effect anymore. We infer it correctly from scope.

### Fixed

- FileResponse and StreamResponse can deduce from scope headers if the request is headless.

## 0.16.5

### Added

- Possibility and alternative way of doing the [dependencies](./dependencies.md) without the need of using the `Provides()`.
The `Provide` is **always required**.

## 0.16.4

### Changed

- Allow providing `notify_fn` as string.

### Fixed

- Fix missing default for `notify_fn` in `SessionFixingMiddleware`.
- Re-add missing dependency `monkay`.
- Fix dependency to `typing-extensions` for python>=3.11.

## 0.16.3

### Changed

- Move `dependencies` from settings to a property based.

### Fixed

- OpenAPIResponse `model` parameters as list.

## 0.16.2

### Added

- Missing `dependencies` in the settings.
- Missing `dependencies` in the `create_client`.
- Add `TrustedReferrerMiddleware`.
- Add `SessionFixingMiddleware`.
- Add `ClientIPScopeOnlyMiddleware` (splitted from `ClientIPMiddleware`).
- Docs concerning security.

### Changed

- Add `block_untrusted_hosts` parameter to `TrustedHostMiddleware`.

### Fixed

- When adding encoders dependencies with `infer_body` as true, it was not filtering the body params properly.

## 0.16.1

### Added

- [Resolve](./dependencies.md#the-resolve-dependency-object) dependency injection functionality. This resolve acts with the `Provider` and
`Provides` as well as a standalone operator. This aims to only to provide an alternative to the already powerful native
dependency injection system of Lilya.

## 0.16.0

### Added

* **Dependency Injection API**

  * Introduced `Provide`/`Provides` pair for declarative DI on handlers
  * Support for three layers of dependencies:

    1. **Application-level** – global services (e.g. database, feature flags)
    2. **Include-level** – sub-application scoping (e.g. per-module configs)
    3. **Route-level** – fine-grained overrides for specific endpoints

* **Handler Parameter Injection**

    * Automatically resolves `Provides()` parameters by name
    * Supports async and sync factory functions
    * Factory chaining: one provider may declare dependencies on another

* **Per-Request Caching**
    * `Provide(..., use_cache=True)` option to memoize within a request

* **WebSocket Support**
    * Inject dependencies into WS routes via the same `Provides()` mechanism

## Changed

* **Scope Handling Fixes**
    * Stabilized `request.scope["app"]` availability across HTTP, WS, and lifespan events

* **Serialization Improvements**
    * Ensured `Provides()` defaults aren't accidentally passed to JSON encoders

### Fixed

* Fixed **KeyError: 'app'** in legacy routing tests when mounting nested includes
* Corrected nested factory resolution so upstream dependencies are auto-wired


## 0.15.6

### Added

- Missing `before_request` and `after_request` to `app.include`.
- `path` to runserver allowing the user to customise the path location of a Lilya app.
- New `LilyaExceptionMiddleware` that intercepts globally any exception that is not only from the handlers.
This can be useful if you want to raise an exception in middlewares and be caught by the exception handlers declared.
You need to also pass a `enable_intercept_global_exceptions` in the `Lilya` instance or [settings](./settings.md) as this
is disabled by default.

### Changed

- Make `reload` in the runserver `False` by default.
- Logging configuration can jump the `configure` if necessary.

## 0.15.5

### Added

- Support for multiplexing a session into multiple session contexts.
- Added support for `redirect_exception` when using [WSGIMiddleware](./middleware.md#wsgimiddleware). This
flag when passed, you can add a `HTTPException` exception handler that will make Lilya capture the WSGI exceptions.
- Exception handlers on a global level can now be passed via [settings](./settings.md)

### Changed

- `SessionContext` has now the methods `set_session`, `get_session`. No more `get/set_connection` is used.
- `infer_body` is more assertive in the error messages.

### Fixed

- Raise proper error when hitting the `inferred` body instead of a broad complicated message.

## 0.15.4

### Added

- Support for a second form of declaring [directives](./directives/directive-decorator.md).
- Support for `@directive` decorator on top of a [Sayer](https://sayer.dymmond.com) command making it a directive as
long as it still follows the directive lookup for files.

### Fixed

- Internal definitions and client optimisations.

## 0.15.3

### Added

- Added optional `infer_body` into the settings. This will allow you to do something like this:

```python
from msgspec import Struct
from pydantic import BaseModel


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


async def process_body(user: User, item: Item):
    return {**user.model_dump(), "sku": item.sku}
```

Where the payload is:

```json
{
    "user": {"name": "lilya", "age": 20},
    "item": {"sku": "test"}
}
```

Assuming you have the [encoders](./encoders.md) for Pydantic and Struct installed in your application (or any other) you
desire.

Lilya uses the internal Encoders to parse and transform them properly.

!!! Note
    `infer_body` is set to `False` by default but you can override it in the [settings](./settings.md).

Another example can be:

```python
from pydantic import BaseModel


class User(BaseModel):
    name: str
    age: int


async def process_body(user: User):
    return user
```

Where here the post can be directly sent like:

```json
{
    "name": "lilya", "age": 20
}
```

### Fixed

- Typing for `settings_module` that was not parsing properly.
- `requestBody` was not displaying when it was required and enabled.
- The parsing of the request body via decorator and BaseHandler if `infer_body` is on.

## 0.15.2

### Fixed

- Migration to Sayer missed the `run` directive argument required as False.
- Missing `apps` when generating a project with structure.

## 0.15.1

### Fixed

- This was supposed to go in the release 0.15.0 but a requirement was missing.

## 0.15.0

### Added

- Support for [OpenAPI](./openapi.md) documentation under the new `@openapi()` decorator. This is optional and can be used
to document your API endpoints with OpenAPI specifications without the need of any external library.

### Changed

- `lilya runserver` is nor revamped with modern UI and logs.
- `lilya runserver` now supports `workers` and `proxy-headers` parameters.

## 0.14.2

### Changed

- Update internals of cli with the latest [Sayer](https://sayer.dymmond.com) version.

## 0.14.1

### Fixed

- `observable` was causing AnyIO problems.

## 0.14.0

Due to type advancements of the ecosystem, it was decided to drop support for Python 3.9 so we can unify syntaxes and tools.

### Added

- Integration with [Sayer](https://sayer.dymmond.com) for the Lilya CLI. This is a massive milestone for Lilya as it allows
you to use the Lilya CLI with the Sayer CLI, which is a powerful tool for managing your Lilya applications or any other, really.

### Changed

- Typing for `add_route` allowing controllers to be recognised.
- Rename `show_urls` directive to `show-urls`. This is a breaking change as the directive name has changed but slightly more
consistent with the rest of the directives.
- Drop support for Python 3.9 due technology advancements.

## 0.13.7

### Added

- Add `populate_context` parameter for `GlobalContextMiddleware`.
- Add `populate_global_context` parameter for `Lilya`.
- Add `populate_session` parameter for `SessionMiddleware`.
- `LifespanGlobalContextMiddleware` which is initializing `g` for lifespans.

### Changed

- `GlobalContextMiddleware` was initializing `g` for lifespans  Now this is moved to `LifespanGlobalContextMiddleware`.

### Fixed

- `SessionContext` was not working for websockets.
- Allow sniffing with `GlobalRequestContext`.

## 0.13.6

### Fixed

- `render_template` was checking the wrong order in the TemplateController and ListController.

## 0.13.5

### Added

- Support for [TemplateController](./templates.md#templatecontroller).
- Support for [ListController](./templates.md#listcontroller).

## 0.13.4

### Changed

- Replace in encoders the contextVar ENCODER_TYPES with a TransparentCage (monkay, works like a ContextVar mixed with a Sequence).
- Lazy evaluate the environment variable for the settings import. This relaxes the restraints on the import order.
  You can e.g. import lilya settings before adjusting `LILYA_SETTINGS_MODULE` as long as you don't access the settings object.

## 0.13.3

### Added

- New [LoggingConfig](./logging.md) for the logging configuration. This now allows you to setup
your own logging system and plug it with anything you want and then use the global logger from Lilya to log your
messages by simply using:

```python
from lilya.logging import logger

logger.info("My message in my logger.")
```
- `StandardLogging` as the new default logging system of Lilya, removing the dependency of `loguru` and make this one
optional.

### Fixed

- Missing `before_request` and `after_request` in the global Lilya settings.

## 0.13.2

### Changed

- Deduplicate code between Router and Lilya. Move methods in a mixin.
- Move some methods and properties from BaseLilya to Lilya.
- **Unprefix** load_settings_value.

## 0.13.1

### Changed

- Proper instance tracking.

## 0.13.0

### Changed

- FileResponse tries to offload the file response to the server in case it supports the extensions.
- [monkay](https://monkay.dymmond.com) as the lazy settings manager.

### Removed

- Old LazyObject settings system allowing for more flexibility from [monkay](https://monkay.dymmond.com).

## 0.12.11

### Added

- [Observables](./observables.md) documentation section. This is a new feature that allows to create
observables that can be used to create a more reactive programming style.

### Fixed

- Header fix for uvicorn wasn't working anymore after a dependency update. Allow bytes header keys.

## 0.12.10

### Fixed

- `override_settings` was not having the override import behaviour expected.

## 0.12.9

### Added

- Missing before and after request in the handler helpers.

## 0.12.8

### Added

- `Lilya`, `Include`, `Host`, `Path` and `Router` now support `before_request` and `after_request`
life cycles. This can be particularly useful to those who want to perform actions before and after
a request is performed. E.g.: Telemetry.
- Added `version` to Lilya client.

### Changed

- Declaring `DefinePermission` became optional as Lilya automatically wraps if not provided.
- Declaring `DefineMiddleware` became optional as Lilya automatically wraps if not provided.
-
### Fixed

- `SessionMiddleware` was creating duplicates because it was called on every lifecycle.

## 0.12.6

### Fixed

- Bug with uvicorn. It assumes the headers in scope being a list instead of an iterator.

## 0.12.5

### Added

- Header is now an iterator which is an alias to encoded_multi_items.
  Instead of reparsing the headers for every middleware, keep the instance and mimic a fitting generator.- `sniff` method on Request.

### Changed

- `receive`, `send` are not properties anymore on Request but proper methods. `receive` has a replay mode for `sniff`.

### Fixed

- StaticFiles without scope headers failed.
- StaticFiles were susceptible for path traversal attacks.
- Calling Request.headers could empty the headers in scope when just a generator.
- Messages were not replayed in case `ContinueRouting` was raised. This prevented sniffing like documented.

## 0.12.4

### Added

- Compatibility mode for async response content.
- Support for jinja enable_async option.

## 0.12.3

### Fixed

- `from_scope` was incorrectly applied in some middleware on scope and not on message for updated message headers.
  This breaks for example post responses.

## 0.12.2

### Fixed

- Context G threads safety

## 0.12.1

### Added

- New [SessionContextMiddleware](./middleware.md#sessioncontextmiddleware) allowing to use the new `session` object
in a request context.

### Changed

- Updated the Context section by adding the [session context](./context.md#the-session-object) examples and explanation
how to use it.

## 0.12.0

### Added

- Support for Python 3.13.
- Add `ReceiveSendSniffer`. This sniffer allows to detect communication events and to replay receive messages.
- `Include` and `BaseLilya` (application) have now a ClassVar `router_class` to provide a custom router.
- Subclasses of `BaseLilya` (application) can set the `router_class` to None to provide a completely custom router
  which initialization parameters aren't required to match the ones of `Router`.
- Expose `fall_through` on `StaticFile`.

### Changed

- The `PathHandler` interface was changed to receive a `ReceiveSendSniffer` instead of `send`/`receive`.
- The `handle_partial` interface was changed to receive a `PathHandler`.
- Fall-through routing was implemented.
- Expose `redirect_slashes` on `Include`.

### Fixed

- `Host` with middleware or permissions.

## 0.11.11

### Fixed

- Some middleware are not multithreading/async capable.

## 0.11.10

### Added

- Add `passthrough_body_types` for passing memoryviews and bytearrays directly to the application server.

### Changed

- TestClient validates more ASGI conformance. It raises an `ASGISpecViolation` error for spec violations when `check_asgi_conformance` is True (default).
- Response's `make_headers` now set `headers` directly.
- Response's `headers` is now a attribute.
- Response's `raw_headers` is now an alias for `encoded_headers`.

### Fixed

- Ensure the response output is bytes when not `passthrough_body_types` is set. Defaults to passing through bytes.
- Properly handle bytearrays.
- Properly parse header values. Properly handle cases in which header values are passed as an array in a dictionary.
- Properly set cookies.


## 0.11.9

### Added

- Add `session_serializer`, `session_deserializer` parameters to `SessionMiddleware`.

### Changed

- Refactor `SessionMiddleware`.
- Refactor authentication.
- Allow multiple backends in `AuthenticationMiddleware`.
- Move backend logic from `BaseAuthMiddleware` to `AuthenticationMiddleware`. Matches documentation.
- Rename BaseUser to UserInterface and make it a protocol. Note: the old name is still available for compatibility reasons.
- Remove undocumented stub definitions from UserInterface. They were unsound.

### Fixed

- Authentication documentation referenced non-existing structures.
- Available middleware section in middleware.md was not up to date.
- Fix serialization of primitives in the Response. Strip `"` by default.

## 0.11.8

### Fixed

- Fix too strict json_encoder_fn enforcment.
- Fix empty [] and {} becoming incorrectly an empty response in json context.

## 0.11.7

### Added

- Add bytes encoder to encoders.
- Allow using DefineMiddleware and DefinePermission with import strings.

### Changed

- Move simplify logic from `make_response` to Response but keep old interface.
- Move esmerald Response `transform` to lilya.

### Fixed

- Fix unnecessary roundtrip in JSONResponse.

## 0.11.6

### Added

- Add `redirect` function as a wrapper to return `ResponseRedirect` responses. Import happens
inside `lilya.responses import redirect`.

### Changed

- Make `g` object automatically managed by Lilya middleware. You no longet need to import the
`GlobalContextMiddleware` as it is a default Lilya middleware.

## 0.11.5

### Added

- `RequestContextMiddleware` added allowing request objects being used without a context of a request
without explicitly declaring it inside handlers.

### Changed

- Allow multiple directories in `StaticFiles`. This enables providing overwrites/defaults.

## 0.11.4

### Added

- `GlobalContextMiddleware` the new middleware that allows you to have `g` object across the
request lifecycle and set global variables to be accessed through that same lifecycle.
- The [g](./context.md#the-g-object) definition and declaration.

### Changed

- Remove hard dependency of `dymmond-settings`.

## 0.11.3

### Changed

- Lilya middleware for Authentication refactored to allow backends to be passed as parameter.

### Fixed

- Ensure encoders used for `apply_structure` have at least `encode` and `is_type_structure`.
  The remaining methods are ensured by `EncodeProtocol` check.

## 0.11.2

### Changed

- Encoders saved on responses are ensured to be instances and not classes.

### Fixed

- Crash when passing string to is_type_structure (e.g. string annotations).
- Fix Encoder type in responses.

## 0.11.1

### Added

- `__encode__` flag to all native encoders.

### Fixed

- `StructureEncoder` __type__ was pointing to the wrong structures.

## 0.11.0

### Changed

- Enhanced encoders:
  - `ENCODER_TYPES` is now a context-variable.
  - New encoders for datetime and date.
  - Former `json_encoder` is now exported via public API as `json_encode`. The old name is still available in `_internal`.
  - New method `apply_structure`, which allows input parsing.
  - `make_response` does not support encoders as class anymore only as instance.

### Fixed

- `typing_extensions` errors on python >= 3.10.
- Address deprecation warnings in tests.
- Fix encoders applied after simplifying response.

## 0.10.2

### Changed

- Lilya is now BSD-3 licence compliant to protect the developers and mantainers.

### Fixed

- `runserver` was not being application agnostic.

## 0.10.1

### Added

- New `ClientIPMiddleware` added allowing retrieving IP information directly.

### Changed

- The Lilya directives now use [Taskfile](https://taskfile.dev) when generating a project.

## 0.10.0

### Changed

- Rename EnvironmentException to EnvException (but keep old name as alias).
- Drop support for python<3.9.
- `ENCODER_TYPES` are now ordered and new encoders are prepend.

## 0.9.1

### Added

- CORSMiddleware now supports the `allow_private_networks` boolean parameter. This prepares
for what is coming for Chromium based browsers.

### Changed

- Internal testing for Edgy with the new drivers.

## 0.9.0

### Added

- The new possibility of declaring routes using lilya as decorator.

#### Example

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import Ok

app = Lilya()


@app.get("/")
async def welcome():
    return Ok({"message": "Welcome to Lilya"})


@app.get("/{user}")
async def user(user: str):
    return Ok({"message": f"Welcome to Lilya, {user}"})


@app.get("/in-request/{user}")
async def user_in_request(request: Request):
    user = request.path_params["user"]
    return Ok({"message": f"Welcome to Lilya, {user}"})
```

## 0.8.3

### Changed

- Internal app generator simple now returns async examples by default.
- Update encoding to be `utf-8` by default.


## 0.8.2

This was supposed to in the version 0.8.1

### Fixed

- LRU caching affecting connections from request.

## 0.8.1

### Changed

- Removed unused middleware.
- Updated AppSettingsMiddleware for lazy loading
- Updated `globalise_settings`.

### Fixed

- Performance issues caused by `AppSettingsModule`.

## 0.8.0

### Added

- `XFrameOptionsMiddleware` to handle with options headers.
- `SecurityMiddleware` adding various security headers to the request/response lifecycle.
- `override_settings` as new decorator that allows to override the Lilya settings in any given test.

### Fixed

- Missing status `HTTP_301_MOVED_PERMANENTLY` from the list of available status.

## 0.7.5

### Added

- Allow path parameters to also be defined with `<>` as alternative to `{}`.

#### Example

```python
from lilya.routing import Path

Path("/<age:int>", ...)
```

## 0.7.4

### Added

- Translations to portuguese.

### Fixed

- Missing `settings` in the `runserver` directive.

## 0.7.3

### Fixed

- Documentation generation for `typing.Unpack`.

## 0.7.2

### Changed

- Optimised the `encoders` and how it evaluates the `ENCODER_TYPES`.
- Internal fixes in the `TestClient` and internals.

## 0.7.1

### Fixed

- Import cast clashing with local variables.

## 0.7.0

### Added

- New [EnvironLoader](./environments.md) support.

### Fixed

- Internal `AsyncExitStack` middleware raising exception.

## 0.6.1

### Changed

- Internal support for `hatch` and removed the need for a `Makefile`
- Documentation references
- Internals for Directives. [#54](https://github.com/dymmond/lilya/pull/54) by [@devkral](https://github.com/devkral).

## 0.6.0

### Fixed

- `add_arguments` from BaseDirective to not raise `NotImplementedError` exception.

## 0.5.0

### Added

- `settings_module` also supports import as string

#### Example

```python
from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path


async def home(): ...


app = Lilya(
    routes=[Path("/", handler=home)],
    settings_module="myapp.configs.settings.AppSettings",
)
```

## 0.4.0

### Added

- `encoders` directly embed in any response. The `encoders` is a list of `lilya.encoder.Encoder` type
of objects that can be passed directly into the response. SInce the responses can be independent ASGI applications,
the encoders can be passed directly there.

## 0.3.5

### Changed

- Documentation improvements.

### Fixed

- Typo in the create project directive urls file descripton.

## 0.3.4

### Added

- Extra validations to handle the events.

## 0.3.3

### Added

- `settings_module` when passed in the instance of Lilya will take precedence
over the global settings, removing the need of using constantly the `LILYA_SETTINGS_MODULE`.
- `ApplicationSettingsMiddleware` as internal that handles with the `settings_module` provided and maps
the context of the settings.

#### Example of the way the settings are evaluated

```python
from dataclasses import dataclass

from lilya.apps import Lilya
from lilya.conf import settings
from lilya.conf.global_settings import Settings
from lilya.responses import Ok
from lilya.routing import Include, Path

async def home():
    title = getattr(settings, "title", "Lilya")
    return Ok({"title": title, "debug": settings.debug})


@dataclass
class NewSettings(Settings):
    title: str = "Settings being parsed by the middleware and make it app global"
    debug: bool = False


@dataclass
class NestedAppSettings(Settings):
    title: str = "Nested app title"
    debug: bool = True


app = Lilya(
    settings_module=NewSettings,
    routes=[
        Path("/home", handler=home),
        Include(
            "/child",
            app=Lilya(
                settings_module=NestedAppSettings,
                routes=[
                    Path("/home", handler=home),
                ],
            ),
        ),
    ],
)
```

In the context of the `controller home`, based on the path being called, it should return the
corresponding value of the `title` according to the settings of the app that is included.

### Changed

- `createapp` directive `views.py` file generated renamed to `controllers.py`.

## 0.3.2

### Fixed

- Missing requirements needed for the `pip install lilya[cli]`

## 0.3.1

### Added

- New `await request.data()` and `await request.text()` .
- `media` to `Request` object returning a dict containing the content type media definitions in a dictionary
like format.

## 0.3.0

### Added

- Allow `Encoder` and `Transformer`  to be registered without forcing to be
instances.

### Changed

- Add `__slots__` to  `Request`.

## 0.2.3

### Added

- Alias `Middleware` to be imported from `lilya.middleware`.

### Fixed

- `message` in responses was not passing the proper headers.

## 0.2.2

### Added

- New lazy loading settings system making it more unique and dynamic.

## 0.2.1

### Changed

- Update internal `dymmond-settings` minimum requirement.

## 0.2.0

### Added

- Support for `len` in `Secret` datastructure.

### Changed

- The way the signature is evaluated in the Path and WebSocketPath
- Internal code refactoring for signature and `include`.

**BREAKING CHANGE**

- `SETTINGS_MODULE` was renamed to `LILYA_SETTINGS_MODULE`.

### Fixed

- `namespace` validation for Include.
- Internal form parser was duplicating the values.

## 0.1.2

### Fixed

- `Transformer` to allow to be hashable from the dataclasses.

## 0.1.1

### Fixed

- Context scope for app not being properly called from the request.

## 0.1.0

Initial release of `Lilya`.

* A lightweight ASGI toolkit.
* Support for HTTP/WebSocket.
* Tasks (in ASGI known as background tasks).
* Lifespan events (on_startup/on_shutdown and lifespan).
* Native permission system.
* Middlewares (Compressor, CSRF, Session, CORS...).
* A native and **optional** [client](./lilya-cli.md).
* **Directive management control system** for any custom scripts to run inside the application.
* Dynamic routing system with the help of the native **Include** and minimum boilerplate.
* Native settings system. No more bloated instances.
