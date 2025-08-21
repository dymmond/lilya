from lilya.apps import Lilya
from lilya.contrib.security.oauth2 import OAuth2PasswordBearer
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Security
from lilya.dependencies import Provides, Provide
from lilya.routing import Path
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    username: str
    email: str | None = None


def fake_decode_token(token):
    return User(username=token + "fakedecoded", email="john@example.com")


async def get_current_user(token: str = Security(oauth2_scheme)):
    user = fake_decode_token(token)
    return user


@openapi(security=[oauth2_scheme])
async def users_me(current_user: User = Provides()) -> User:
    return current_user


app = Lilya(
    routes=[
        Path(
            "/users/me",
            handler=users_me,
            dependencies={"current_user": Provide(get_current_user)}
        ),
    ],
)