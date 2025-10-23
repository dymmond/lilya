import base64
import binascii

from lilya.apps import Lilya
from lilya.authentication import (
    AuthCredentials, AuthenticationBackend, BasicUser, AuthResult
)
from lilya.exceptions import AuthenticationError
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.requests import Connection, Request



class SessionBackend(AuthenticationBackend):
    async def authenticate(self, connection: Connection) -> None | AuthResult:
        if "session" not in connection.scope:
            return None

        if connection.scope["session"].get("username", None):
            return None
        return AuthCredentials(["authenticated"]), BasicUser(connection.scope["session"]["username"])


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, connection: Connection) -> None | AuthResult:
        if "Authorization" not in connection.headers:
            return None

        auth = connection.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != 'basic':
                return None
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError('Invalid basic auth credentials')

        username, _, password = decoded.partition(":")
        return AuthCredentials(["authenticated"]), BasicUser(username)


async def homepage(request: Request)-> PlainText:
    if request.user.is_authenticated:
        return PlainText('Hello, ' + request.user.display_name)
    return PlainText('Hello, you')


routes = [
    Path("/", handler=homepage)
]

middleware: list[DefineMiddleware] = [
    # must be defined before AuthenticationMiddleware, because of the SessionBackend
    DefineMiddleware(SessionMiddleware, secret_key=...),
    DefineMiddleware(AuthenticationMiddleware, backend=[SessionBackend(), BasicAuthBackend()])
]

app = Lilya(routes=routes, middleware=middleware)
