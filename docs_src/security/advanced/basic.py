from lilya.apps import Lilya
from lilya.contrib.security.http import HTTPBasic, HTTPBasicCredentials
from lilya.contrib.openapi.decorator import openapi
from lilya.dependencies import Provides, Provide
from lilya.routing import Path

security = HTTPBasic()


@openapi(security=[security])
def get_current_user(credentials: HTTPBasicCredentials = Provides()) -> dict[str, str]:
    return {"username": credentials.username, "password": credentials.password}


app = Lilya(
    routes=[
        Path(
            "/users/me",
            handler=get_current_user,
            dependencies={"credentials": Provide(security)},
        )
    ]
)
