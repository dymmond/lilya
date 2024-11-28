# Authentication

Lilya provides a straightforward yet robust interface for managing authentication and permissions. 
By installing `AuthenticationMiddleware` with a suitable authentication backend, you can access the `request.user` and `request.auth`
interfaces within your endpoints.


```python
import base64
import binascii

from lilya.apps import Lilya
from lilya.authentication import (
    AuthCredentials, AuthenticationBackend, AuthenticationError, BasicUser
)
from lilya.middleware import DefineMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.responses import PlainText
from lilya.routing import Path


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, connection):
        if "Authorization" not in connection.headers:
            return

        auth = connection.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != 'basic':
                return
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError('Invalid basic auth credentials')

        username, _, password = decoded.partition(":")
        return AuthCredentials(["authenticated"]), BasicUser(username)


async def homepage(request):
    if request.user.is_authenticated:
        return PlainTextResponse('Hello, ' + request.user.display_name)
    return PlainTextResponse('Hello, you')


routes = [
    Path("/", handler=homepage)
]

middleware = [
    Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())
]

app = Lilya(routes=routes, middleware=middleware)
```

## Users

Once you have installed `AuthenticationMiddleware`, the `request.user` interface becomes 
available to your endpoints and other middleware.

This interface should subclass `BaseUser`, which includes two properties and any additional information your user model requires.

* `.is_authenticated`
* `.display_name`

Lilya provides two built-in user implementations: `AnonymousUser()`,
and `BasicUser(username)`.

## AuthCredentials

Authentication credentials should be considered distinct from user identities.
An authentication scheme must be capable of granting or restricting specific privileges independently of the user's identity.

The `AuthCredentials` class provides the basic interface that `request.auth`
exposes:

* `.scopes`

## Permissions

Permissions are enforced using an endpoint decorator that ensures the incoming request contains the necessary authentication scopes.

```python
from lilya.authentication import requires


@requires('authenticated')
async def dashboard():
    ...
```

You can include either one or multiple required scopes:

```python
from lilya.authentication import requires


@requires(['authenticated', 'admin'])
async def dashboard():
    ...
```

By default, a 403 response is returned when permissions are not granted. However, you may want to customize this behavior to prevent revealing information about the URL structure to unauthenticated users.

```python
from lilya.authentication import requires


@requires(['authenticated', 'admin'], status_code=404)
async def dashboard():
    ...
```

!!! Note
    The `status_code` parameter is not applicable for WebSockets. For WebSocket connections, a 403 (Forbidden) status code will always be used.
    Alternatively, you may want to redirect unauthenticated users to a different page.

```python
from lilya.authentication import requires


async def homepage():
    ...


@requires('authenticated', redirect='homepage')
async def dashboard():
    ...
```

When redirecting users, the destination page will include the original URL they requested in the `next` query parameter:

```python
from lilya.authentication import requires
from lilya.responses import RedirectResponse


@requires('authenticated', redirect='login')
async def admin():
    ...


async def login(request):
    if request.method == "POST":
        # Now that the user is authenticated,
        # we can send them to their original request destination
        if request.user.is_authenticated:
            next_url = request.query_params.get("next")
            if next_url:
                return RedirectResponse(next_url)
            return RedirectResponse("/")
```

For class-based controllers, apply the decorator to the specific method within the class.

```python
from lilya.authentication import requires
from lilya.controllers import Controller


class Dashboard(Controller):
    @requires("authenticated")
    async def get(self, request):
        ...
```

## Custom authentication error responses

You can customize the error response sent when an `AuthenticationError` is raised by an authentication backend:

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse


def on_auth_error(request: Request, exc: Exception):
    return JSONResponse({"error": str(exc)}, status_code=401)

app = Lilya(
    middleware=[
        Middleware(AuthenticationMiddleware, backend=BasicAuthBackend(), on_error=on_auth_error),
    ],
)
```