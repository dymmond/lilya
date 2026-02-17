# lilya/_internal/ — Private Implementation Layer

## Overview
This directory contains the private implementation details of Lilya. These modules are not part of the public API and should not be imported directly by end-users. For a stable API, always use the top-level re-export modules (e.g., `lilya.encoders`, `lilya.transformers`).

## Module Reference

### _connection.py
- **Purpose**: Provides the base `Connection` class used by `Request` and `WebSocket` to manage ASGI scope and state (URL, headers, cookies, etc.).
- **Public vs Internal**: Internal base class.
- **Stability**: Internal - Can change without notice.
- **Key API**: `Connection`, `empty_receive`, `empty_send`, `ClientDisconnect`.
- **Usage**: Foundation for `lilya.requests.Request` and `lilya.websockets.WebSocket`.

### _crypto.py
- **Purpose**: Cryptographic helpers for generating securely random strings and secret keys.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `get_random_string`, `get_random_secret_key`.
- **Usage**: Used by CLI directives for project/app scaffolding and in CSRF middleware tests.

### _encoders.py
- **Purpose**: Extensible encoding and decoding system for JSON serialization and data molding (TransparentCage pattern).
- **Public vs Internal**: Re-exported via `lilya.encoders`.
- **Stability**: Stable - Re-exported via public API.
- **Key API**: `Encoder`, `EncoderProtocol`, `MoldingProtocol`, `register_encoder`, `json_encode`, `apply_structure`.
- **Usage**: Central to JSON responses and parameter binding in handlers.

### _encoding.py
- **Purpose**: Utilities for string encoding and conversion, ensuring safe type handling.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `force_str`, `is_protected_type`, `ExtraUnicodeDecodeError`.
- **Usage**: Used in exception handling and by internal parsers.

### _events.py
- **Purpose**: Logic for handling ASGI lifespan events (startup/shutdown) and a lightweight observable `EventDispatcher`.
- **Public vs Internal**: Internal helpers; `EventDispatcher` is re-exported via `lilya.decorators`.
- **Stability**: Mixed - Internal for lifespan, Stable for `EventDispatcher`.
- **Key API**: `AsyncLifespan`, `handle_lifespan_events`, `EventDispatcher`.
- **Usage**: App bootstrap in `apps.py` and routing in `routing.py`.

### _exception_handlers.py
- **Purpose**: Logic for looking up and executing exception handlers based on exception type or HTTP status code.
- **Public vs Internal**: Internal logic.
- **Stability**: Internal - Can change without notice.
- **Key API**: `wrap_app_handling_exceptions`, `handle_exception`, `_lookup_exception_handler`.
- **Usage**: Core component of `ExceptionMiddleware`.

### _helpers.py
- **Purpose**: HTTP header related helpers, specifically for identifying and removing entity headers according to RFC 2616.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `HeaderHelper`.
- **Usage**: Heavily used by `lilya.responses`.

### _inspect.py
- **Purpose**: Introspection utility to check if a function accepts `**kwargs`.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `func_accepts_kwargs`.
- **Usage**: Used by `EventDispatcher` and other introspection-heavy logic.

### _message.py
- **Purpose**: Simple data structures for representing network addresses and ASGI messages.
- **Public vs Internal**: Internal.
- **Stability**: Internal - Can change without notice.
- **Key API**: `Address` dataclass.
- **Usage**: Used by `Connection` internals.

### _middleware.py
- **Purpose**: Helper to ensure middleware is correctly wrapped in `DefineMiddleware` instances.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `wrap_middleware` (with `lru_cache`).
- **Usage**: Used during app and router initialization to normalize middleware stacks.

### _module_loading.py
- **Purpose**: Dynamic import utility to load classes or attributes from a dotted string path.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `import_string`.
- **Usage**: Used by CLI, settings resolution, and Monkay bootstrap.

### _parsers.py
- **Purpose**: Robust parsers for cookies and form data (urlencoded and multipart).
- **Public vs Internal**: Internal; requires `python-multipart` for form parsing.
- **Stability**: Internal - Can change without notice.
- **Key API**: `cookie_parser`, `FormParser`, `MultiPartParser`.
- **Usage**: Core to `Request` object for parsing incoming data.

### _path.py
- **Purpose**: Logic for path manipulation, regex compilation for routing, and path parameter extraction.
- **Public vs Internal**: Internal logic.
- **Stability**: Internal - Can change without notice.
- **Key API**: `clean_path`, `compile_path`, `replace_params`, `parse_path`.
- **Usage**: Foundational for `routing.py` and `staticfiles.py`.

### _path_transformers.py
- **Purpose**: Built-in and custom path parameter type converters (string, int, float, uuid, datetime).
- **Public vs Internal**: Re-exported via `lilya.transformers`.
- **Stability**: Stable - Re-exported via public API.
- **Key API**: `Transformer`, `register_path_transformer`, `TRANSFORMER_TYPES`.
- **Usage**: Used by `routing.py` to convert path segments into Python types.

### _permissions.py
- **Purpose**: Helper to ensure permission is correctly wrapped in `DefinePermission` instances.
- **Public vs Internal**: Internal utility.
- **Stability**: Internal - Can change without notice.
- **Key API**: `wrap_permission` (with `lru_cache`).
- **Usage**: Used during app and router initialization to normalize permission stacks.

### _representation.py
- **Purpose**: Base classes for object representations (`__repr__`, `__str__`), including support for `devtools` and `Rich`.
- **Public vs Internal**: Internal base; `Repr` is used by many core data structures.
- **Stability**: Internal - Can change without notice.
- **Key API**: `BaseRepr`, `Repr`.
- **Usage**: Inherited by `BackgroundTasks`, `URL`, and various datastructures.

### _responses.py
- **Purpose**: The engine for handler resolution. Manages signature introspection, dependency injection, parameter binding, and execution.
- **Public vs Internal**: Internal base class `BaseHandler`.
- **Stability**: Internal - HIGH COMPLEXITY (1210 LOC).
- **Key API**: `BaseHandler`, `resolve_signature_annotations`, `handle_response`.
- **Usage**: Inherited by `Path` and controllers to handle the request-response cycle.

### _scopes.py
- **Purpose**: Central registry for managing dependency instances across GLOBAL, APP, and REQUEST scopes.
- **Public vs Internal**: Internal DI registry.
- **Stability**: Internal - Can change without notice.
- **Key API**: `ScopeManager`, `scope_manager` singleton.
- **Usage**: Backing store for `lilya.dependencies`.

### _urls.py
- **Purpose**: Utilities for URL inclusion (`include`) and reversal (`reverse`).
- **Public vs Internal**: `include` is re-exported via `lilya.routing`; `reverse` via `lilya.compat`.
- **Stability**: Stable - Re-exported via public API.
- **Key API**: `include`, `reverse`.
- **Usage**: Used for nested routing and URL building.

### _templates/
- **Purpose**: Jinja2 templates used by the Lilya CLI for scaffolding.
- **Public vs Internal**: Internal assets.
- **Stability**: Internal - Must match CLI directive requirements.
- **Key Assets**: `project_template`, `app_template`, `deployment_template`.
- **Usage**: `lilya-cli create-project` and related commands.

## Contributor Guide

### When to add code to `_internal/`
- **Foundational Helpers**: Logic that is shared across multiple core modules (e.g., `apps.py` and `routing.py`).
- **Complex Implementations**: Long or complex logic that would clutter public modules (e.g., `_responses.py`).
- **Private Parsers**: Parsers for specific formats (cookies, multipart) that don't need a public face.

### Stability and Public API
- **Avoid Direct Imports**: Never import from `_internal` in external code.
- **The Re-export Pattern**: If a helper needs to be public, define it in `_internal` and re-export it in a top-level module (e.g., `lilya/encoders.py`).
- **High-Risk Modules**: `_responses.py` and `_path.py` are critical to the framework's performance and correctness. Changes here must be verified with broad test coverage.
