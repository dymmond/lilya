---
hide:
  - navigation
---

# Lilya

<p align="center">
  <a href="https://lilya.dev"><img src="https://res.cloudinary.com/dymmond/image/upload/v1707501404/lilya/logo_quiotd.png" alt='Lilya'></a>
</p>

<p align="center">
    <em>🚀 Yet another ASGI toolkit that delivers. 🚀</em>
</p>

<p align="center">
<a href="https://github.com/dymmond/lilya/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" target="_blank">
    <img src="https://github.com/dymmond/lilya/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" alt="Test Suite">
</a>

<a href="https://pypi.org/project/lilya" target="_blank">
    <img src="https://img.shields.io/pypi/v/lilya?color=%2334D058&label=pypi%20package" alt="Package version">
</a>

<a href="https://pypi.org/project/lilya" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/lilya.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentation**: [https://lilya.dev](https://lilya.dev) 📚

**Source Code**: [https://github.com/dymmond/lilya](https://github.com/dymmond/lilya)

**The official supported version is always the latest released**.

---

## Motivation

In the world of ASGI, alternatives are always great to have and no tool serves it all.
Lilya, coming from the great inspirations of the ones who paved the way, its a more simple, accurate
fast and easy to use Python toolkit/framework that aims for simplicity.

A lot of times you won't be needing a fully fledge Python web framework as it can be overwhelming
for some simple tasks, instead you would prefer a simple ASGI toolkit that helps you designing
production ready, fast, elegant, maintainable and modular applications.

This is where Lilya places itself.

Almost no hard dependencies, 100% pythonic and ready for production.

## What does it bring?

Lilya comes bearing fruits.

* A lightweight ASGI toolkit/framework.
* Support for HTTP/WebSocket.
* Tasks (in ASGI known as background tasks).
* Lifespan events (on_startup/on_shutdown and lifespan).
* Native permission system.
* Middlewares (Compressor, CSRF, Session, CORS...).
* A native and **optional** cli.
* `Directive management control system` for any custom scripts to run inside the application.
* Very little hard dependencies.
* Compatibility with `trio` and `asyncio`.
* Dynamic routing system with the help of the native **Include** and minimum boilerplate.
* Native setting system. No more bloated instances.
