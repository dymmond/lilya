---
hide:
  - navigation
---

# Release Notes

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
