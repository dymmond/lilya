from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware
from lilya.responses import PlainText
from lilya.routing import Path


def test_xframe_options_deny_responses(test_client_factory):
    def homepage():
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(XFrameOptionsMiddleware)],
    )

    client = test_client_factory(app)

    response = client.get("/")

    assert response.headers["x-frame-options"] == "DENY"
