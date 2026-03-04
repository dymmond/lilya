# First Production Run

This guide turns a local app into a production-shaped runtime setup.

## 1. Configure settings explicitly

Use an explicit settings class for environment-specific behavior.

```shell
LILYA_SETTINGS_MODULE=src.configs.production.ProductionSettings palfrey myapp:app
```

See [Settings](../settings.md) for precedence details.

## 2. Pick an ASGI server strategy

Common choices:

- `palfrey` for Lilya-native workflows
- `uvicorn` for broad ecosystem compatibility
- `hypercorn` for multiple async backends

## 3. Apply minimum production baseline

- `debug=False`
- Host validation via [TrustedHostMiddleware](../middleware/trustedhost.md)
- Structured logging via [Logging](../logging.md)
- Shared cache backend for multi-worker environments
- Health endpoint and smoke test

## 4. Add deployment packaging

Use the deployment docs for containerized and non-containerized setups:

- [Deployment Fundamentals](../intro.md)
- [Docker Deployment](../docker.md)

## Related concepts

- [Layering and Precedence](../concepts/layering-and-precedence.md)
- [Component Interactions](../concepts/component-interactions.md)

## Next steps

- [Production Readiness Checklist](../guides/production-readiness-checklist.md)
- [Troubleshooting](../troubleshooting.md)
