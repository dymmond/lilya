from lilya.apps import Lilya
from lilya.conf import settings
from lilya.conf.global_settings import Settings
from lilya.responses import JSONResponse
from lilya.routing import Include, Path
from lilya.testclient import create_client


async def home() -> JSONResponse:
    title = getattr(settings, "title", "Lilya")
    return JSONResponse({"title": title, "debug": settings.debug})


class NewSettings(Settings):
    title: str = "Settings being parsed by the middleware and make it app global"
    debug: bool = False


class NestedAppSettings(Settings):
    title: str = "Nested app title"
    debug: bool = True


def test_app_settings_middleware(test_client_factory):
    with create_client(
        settings_module=NewSettings,
        routes=[Path("/home", handler=home)],
    ) as client:
        response = client.get("/home")

        assert response.json() == {
            "title": "Settings being parsed by the middleware and make it app global",
            "debug": False,
        }


def test_app_settings_middleware_nested_with_child_esmerald(test_client_factory):
    with create_client(
        settings_module=NewSettings,
        routes=[
            Path("/home", handler=home),
            Include(
                "/child",
                app=Lilya(
                    settings_module=NestedAppSettings,
                    routes=[
                        Path("/home", handler=home),
                    ],
                ),
            ),
        ],
    ) as client:
        response = client.get("/home")

        assert response.json() == {
            "title": "Settings being parsed by the middleware and make it app global",
            "debug": False,
        }

        response = client.get("/child/home")

        assert response.json() == {"title": "Nested app title", "debug": True}


def test_app_settings_middleware_nested_with_child_esmerald_and_global(
    test_client_factory,
):
    with create_client(
        settings_module=NewSettings,
        routes=[
            Path("/home", handler=home),
            Include(
                "/child",
                app=Lilya(
                    settings_module=NestedAppSettings,
                    routes=[
                        Path("/home", handler=home),
                    ],
                ),
            ),
            Include(
                "/another-child",
                app=Lilya(
                    routes=[
                        Path("/home", handler=home),
                    ],
                ),
            ),
        ],
    ) as client:
        response = client.get("/home")

        assert response.json() == {
            "title": "Settings being parsed by the middleware and make it app global",
            "debug": False,
        }

        response = client.get("/child/home")

        assert response.json() == {"title": "Nested app title", "debug": True}

        response = client.get("/another-child/home")

        assert response.json() == {
            "title": "Settings being parsed by the middleware and make it app global",
            "debug": False,
        }
