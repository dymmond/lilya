---
hide:
  - navigation
---

# Release Notes

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
