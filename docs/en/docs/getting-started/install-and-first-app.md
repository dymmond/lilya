# Install and First App

This guide gives you a minimal Lilya app and the exact commands to run it.

## Install

Core package:

```shell
pip install lilya
```

If you also want the Lilya client tools:

```shell
pip install lilya[standard]
```

## Build a first app

```python
{!> ../../../docs_src/quickstart/app.py !}
```

## Run it

```shell
palfrey myapp:app --reload
```

Then open `http://127.0.0.1:8000`.

## What this app already demonstrates

- Route declaration with `Path`
- Path parameter injection into handlers
- Native response objects

## Related concepts

- [ASGI Mental Model](../concepts/asgi-mental-model.md)
- [Request Lifecycle](../concepts/request-lifecycle.md)

## Next steps

1. [First Production Run](./first-production-run.md)
2. [Build a Modular API](../tutorials/build-a-modular-api.md)
