from structlog import get_logger

from lilya.responses import PlainText
from lilya.routing import Include, Path
from lilya.testclient import create_client

logger = get_logger()


class BeforePathRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request += 1
        logger.info(f"Before path request: {app.state.app_request}")


class AfterPathRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request += 1

        logger.info(f"After path request: {app.state.app_request}")


class BeforeIncludeRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request += 1
        logger.info(f"Before include request: {app.state.app_request}")


class AfterIncludeRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request += 1

        logger.info(f"After include request: {app.state.app_request}")


class BeforeAppRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request = 1
        logger.info(f"Before app request: {app.state.app_request}")


class AfterAppRequest:
    def __call__(self, scope, receive, send):
        app = scope["app"]
        app.state.app_request += 1

        logger.info(f"After app request: {app.state.app_request}")


def test_all_layers_request():
    async def index(request):
        state = request.app.state
        return PlainText(f"State: {state.app_request}")

    with create_client(
        routes=[
            Include(
                "/",
                routes=[
                    Path(
                        "/",
                        index,
                        before_request=[BeforePathRequest],
                        after_request=[AfterPathRequest],
                    )
                ],
                before_request=[BeforeIncludeRequest],
                after_request=[AfterIncludeRequest],
            ),
        ],
        before_request=[BeforeAppRequest],
        after_request=[AfterAppRequest],
    ) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.text == "State: 3"
