# Production Readiness Checklist

Use this checklist before promoting a Lilya service to production.

## Runtime and settings

- `debug=False`
- Explicit `LILYA_SETTINGS_MODULE` per environment
- Configuration values validated on startup

## Security baseline

- Trusted hosts configured
- HTTPS redirect enabled where required
- Session/CSRF policies reviewed
- Authentication and permission boundaries validated

## Reliability baseline

- Health endpoint exposed
- Graceful startup/shutdown validated
- Timeouts and retry policy defined for external calls

## Observability baseline

- Structured logging enabled
- Error tracking pipeline configured
- Request correlation or trace identifiers present

## Deployment baseline

- Container image pinned and reproducible
- Startup command documented
- Rollback plan tested

## Related references

- [Deployment Fundamentals](../intro.md)
- [Docker Deployment](../docker.md)
- [Security](../security.md)
- [Lifecycle](../lifecycle.md)
