# Migration from FastAPI

This guide helps teams move incrementally from FastAPI to Lilya.

## Migration strategy

1. Start with one bounded feature module
2. Recreate routing and dependencies first
3. Port middleware and permissions next
4. Move tests and verify behavior parity

## Mapping guide

| FastAPI concept | Lilya equivalent |
| --- | --- |
| `FastAPI()` | `Lilya()` |
| `APIRouter` | `Router` or `Include` + route lists |
| `Depends` (request-scoped) | `Provide` + `Provides` |
| Middleware | Middleware protocol / `DefineMiddleware` |
| Exception handlers | `exception_handlers` per layer |

## Recommended sequence

- Migrate read-only routes first
- Migrate auth-protected routes second
- Migrate websocket endpoints last

## Useful tools

- [Lilya Converter](https://lilya-converter.dymmond.com/)
- [Routing](../routing.md)
- [Dependencies](../dependencies.md)
- [Authentication](../authentication.md)

## Validation checklist

- Endpoint behavior parity
- Error shape parity
- Auth and permission parity
- Load/performance smoke check
