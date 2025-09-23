
import base64
import binascii

from lilya.apps import Lilya
from lilya.authentication import (
    AuthCredentials, AuthenticationBackend, BasicUser
)
from lilya.exceptions import AuthenticationError
from lilya.middleware import DefineMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
import secrets



class HardCodedBasicAuthBackend(AuthenticationBackend):
    def __init__(
        self, *, username: str = "admin", password: str
    ) -> None:
        self.basic_string = base64.b64encode(f"{username}:{password}".encode()).decode()

    async def authenticate(self, connection):
        if "Authorization" not in connection.headers:
            return

        auth = connection.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != 'basic':
                return
            if not secrets.compare_digest(credentials, self.basic_string):
                raise ValueError()
            username = base64.b64decode(credentials).decode("ascii").split(":", 1)[0]
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError('Invalid basic auth credentials')

        return AuthCredentials(["authenticated"]), BasicUser(username)


async def homepage(request):
    if request.user.is_authenticated:
        return PlainText('Hello, ' + request.user.display_name)
    return PlainText('Hello, you')


routes = [
    Path("/", handler=homepage)
]

middleware = [
    DefineMiddleware(AuthenticationMiddleware, backend=[HardCodedBasicAuthBackend(password="password")])
]

app = Lilya(routes=routes, middleware=middleware)
