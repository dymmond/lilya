from structlog import get_logger

from lilya.responses import PlainText
from lilya.routing import Include, Path
from lilya.testclient import create_client

logger = get_logger()


def before_path_request(scope, receive, send):
    app = scope["app"]
    app.state.app_request += 1
    logger.info(f"Before path request: {app.state.app_request}")


def after_path_request(scope, receive, send):
    app = scope["app"]
    app.state.app_request += 1

    logger.info(f"After path request: {app.state.app_request}")


def before_include_request(scope, receive, send):
    app = scope["app"]
    app.state.app_request += 1
    logger.info(f"Before include request: {app.state.app_request}")


def after_include_request(scope, receive, send):
    app = scope["app"]
    app.state.app_request += 1

    logger.info(f"After include request: {app.state.app_request}")


def before_app_request(scope, receive, send):
    app = scope["app"]
    app.state.app_request = 1
    logger.info(f"Before app request: {app.state.app_request}")


def after_app_request(scope, receive, send):
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
                        before_request=[before_path_request],
                        after_request=[after_path_request],
                    )
                ],
                before_request=[before_include_request],
                after_request=[after_include_request],
            ),
        ],
        before_request=[before_app_request],
        after_request=[after_app_request],
    ) as client:
        response = client.get("/")

        assert response.status_code == 200
        assert response.text == "State: 3"
