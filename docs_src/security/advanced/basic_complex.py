import secrets

from lilya import status
from lilya.apps import Lilya
from lilya.exceptions import HTTPException
from lilya.routing import Path
from lilya.dependencies import Provide, Provides, Security
from lilya.dependencies import Security
from lilya.contrib.security.http import HTTPBasic, HTTPBasicCredentials
from lilya.contrib.openapi.decorator import openapi

security = HTTPBasic()


def get_username(credentials: HTTPBasicCredentials = Security(security)):
    correct_username = "alice123"
    correct_password = "sunshine"

    if not (
        secrets.compare_digest(credentials.username, correct_username)
        and secrets.compare_digest(credentials.password, correct_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@openapi(security=[security])
def get_current_user(username: str = Provides()) -> dict[str, str]:
    return {"username": username}


app = Lilya(
    routes=[
        Path(
            "/users/me",
            handler=get_current_user,
            dependencies={"username": Provide(get_username)},
        ),
    ],
)
