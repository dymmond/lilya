from myapp.models import User
from myapp.security.jwt.token import Token
from saffier.exceptions import ObjectNotFound

from lilya._internal._connection import Connection
from lilya.exceptions import NotAuthorized
from lilya.middleware.authentication import AuthResult, BaseAuthMiddleware
from lilya.types import ASGIApp


class JWTAuthMiddleware(BaseAuthMiddleware):
    """
    An example how to integrate and design a JWT authentication
    middleware assuming a `myapp` in Lilya.
    """

    def __init__(
        self,
        app: ASGIApp,
        signing_key: str,
        algorithm: str,
        api_key_header: str,
    ):
        super().__init__(app)
        self.app = app
        self.signing_key = signing_key
        self.algorithm = algorithm
        self.api_key_header = api_key_header

    async def retrieve_user(self, user_id) -> User:
        try:
            return await User.get(pk=user_id)
        except ObjectNotFound:
            raise NotAuthorized()

    async def authenticate(self, request: Connection) -> AuthResult:
        token = request.headers.get(self.api_key_header)

        if not token:
            raise NotAuthorized("JWT token not found.")

        token = Token.decode(token=token, key=self.signing_key, algorithm=self.algorithm)

        user = await self.retrieve_user(token.sub)
        return AuthResult(user=user)
