import pytest
from tests.settings import TestSettings

from lilya.app import ChildLilya, Lilya
from lilya.exceptions import ImproperlyConfigured
from lilya.routing import Include, Path, WebSocketPath
from lilya.websockets import WebSocket


class CommonConfig(TestSettings):
    enforce_return_annotation: bool = True


def xtest_raise_error_on_missing_annotation():
    def homepage(): ...  # pragma: no cover

    async def websocket_handler(session: WebSocket): ...  # pragma: no cover

    with pytest.raises(ImproperlyConfigured):
        Lilya(routes=[Path("/home", homepage)], settings_module=CommonConfig)

    with pytest.raises(ImproperlyConfigured):
        Lilya(routes=[WebSocketPath("/ws", websocket_handler)], settings_module=CommonConfig)


def xtest_raise_error_on_missing_annotation_in_child_lilya():
    def homepage(): ...  # pragma: no cover

    async def websocket_handler(session: WebSocket): ...  # pragma: no cover

    with pytest.raises(ImproperlyConfigured):
        Lilya(
            routes=[
                Include(
                    "/",
                    app=ChildLilya(
                        routes=[
                            Path("/home", homepage),
                        ]
                    ),
                )
            ],
            settings_module=CommonConfig,
        )

    with pytest.raises(ImproperlyConfigured):
        Lilya(
            routes=[
                Include(
                    "/",
                    app=ChildLilya(
                        routes=[
                            Path("/home", websocket_handler),
                        ]
                    ),
                ),
            ],
            settings_module=CommonConfig,
        )
