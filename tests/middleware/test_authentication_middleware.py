from lilya import status
from lilya.authentication import AuthCredentials, AuthenticationBackend, AuthResult, BasicUser
from lilya.middleware import DefineMiddleware
from lilya.middleware.authentication import AuthenticationMiddleware
from lilya.requests import Connection, Request
from lilya.responses import PlainText, RedirectResponse
from lilya.routing import Include, Path
from lilya.testclient import create_client

dummy = BasicUser("Dummy")


class DenyNotAllowAll(AuthenticationBackend):
    async def authenticate(self, connection: Connection) -> AuthResult | None:
        if connection.headers.get("allow-all") == "yes":
            return (AuthCredentials(["authenticated"]), dummy)
        return None


def test_auth_app_level(test_client_factory):
    async def homepage(request: Request) -> PlainText:
        if request.headers.get("allow-all") == "yes":
            return PlainText(request.user.display_name)
        else:
            return PlainText("Should not be reached")

    with create_client(
        routes=[Path(path="/", handler=homepage, methods=["GET"])],
        middleware=[DefineMiddleware(AuthenticationMiddleware, backend=[DenyNotAllowAll()])],
    ) as client:
        response = client.get("/", headers={"allow-all": "yes"})
        assert response.status_code == status.HTTP_200_OK
        assert response.text == "Dummy"

        response = client.get("/")
        assert response.text != "Should not be reached"
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_auth_include_level(test_client_factory):
    async def login(request: Request) -> PlainText:
        return PlainText("logged in")

    async def homepage(request: Request) -> PlainText:
        if request.headers.get("allow-all") == "yes":
            return PlainText(request.user.display_name)
        else:
            return PlainText("Should not be reached")

    with create_client(
        routes=[
            Path(path="/login", handler=login, methods=["GET"]),
            Include(
                "",
                routes=[Path(path="/", handler=homepage, methods=["GET"])],
                middleware=[
                    DefineMiddleware(
                        AuthenticationMiddleware,
                        backend=[DenyNotAllowAll()],
                        on_error=RedirectResponse("/login"),
                    )
                ],
            ),
        ],
    ) as client:
        response = client.get("/login")
        assert response.status_code == status.HTTP_200_OK
        assert response.text == "logged in"

        response = client.get("/", headers={"allow-all": "yes"})
        assert response.status_code == status.HTTP_200_OK
        assert response.text == "Dummy"

        response = client.get("/", follow_redirects=False)
        assert response.text != "Should not be reached"
        assert response.status_code == status.HTTP_303_SEE_OTHER
