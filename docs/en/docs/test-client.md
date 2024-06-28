# Test Client

Lilya comes with a test client for your application tests. It is not mandatory use it as every application and
development team has its own way of testing it but just in case, it is provided.

## Requirements

This section requires the Lilya testing suite to be installed. You can do it so by running:

```shell
$ pip install Lilya[test]
```

## The test client

```python
{!> ../../../docs_src/testclient/example1.py !}
```

You can use any of the `httpx` standard API like authentication, session cookies and file uploads.

```python
{!> ../../../docs_src/testclient/example2.py !}
```

**TestClient**

```python
{!> ../../../docs_src/testclient/example3.py !}
```

`httpx` is a great library created by the same author of `Starlette` and `Django Rest Framework`.

!!! Info
    By default the TestClient raise any exceptions that occur in the application.
    Occasionally you might want to test the content of 500 error responses, rather than allowing client to raise the
    server exception. In this case you should use `client = TestClient(app, raise_server_exceptions=False)`.

## Lifespan events

!!! Note
    Lilya supports all the lifespan events available and therefore `on_startup`, `on_shutdown` and `lifespan` are
    also supported by `TestClient` **but** if you need to test these you will need to run `TestClient`
    as a context manager or otherwise the events will not be triggered when the `TestClient` is instantiated.

Lilya also brings a ready to use functionality to be used as context manager for your tests, the `create_client`.

### Context manager `create_client`

This function is prepared to be used as a context manager for your tests and ready to use at any given time.

```python
{!> ../../../docs_src/testclient/example4.py !}
```

The tests work with both `sync` and `async` functions.

!!! info
    The example above is used to also show the tests can be as complex as you desire and it will work with the
    context manager.

## override_settings

This is a special decorator from Lilya and serves as the helper for your tests when you need to update/change
the settings for a given test temporarily to test any scenario that requires specific settings to have different values.

The `override_settings` acts as a normal function decorator or as a context manager.

The settings you can override are the ones declared in the [settings](./settings.md).

```python
from lilya.testclient import override_settings
```

Let us see an example.

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient.utils import override_settings


@override_settings(x_frame_options="SAMEORIGIN")
def test_xframe_options_same_origin_responses(test_client_factory):
    def homepage():
        return PlainText("Ok", status_code=200)

    app = Lilya(
        routes=[Path("/", handler=homepage)],
        middleware=[DefineMiddleware(XFrameOptionsMiddleware)],
    )

    client = test_client_factory(app)

    response = client.get("/")

    assert response.headers["x-frame-options"] == "SAMEORIGIN"
```

Or as context manager.

```python
from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clickjacking import XFrameOptionsMiddleware
from lilya.responses import PlainText
from lilya.routing import Path
from lilya.testclient.utils import override_settings


def test_xframe_options_same_origin_responses(test_client_factory):
    def homepage():
        return PlainText("Ok", status_code=200)

    with override_settings(x_frame_options="SAMEORIGIN"):
        app = Lilya(
            routes=[Path("/", handler=homepage)],
            middleware=[DefineMiddleware(XFrameOptionsMiddleware)],
        )

        client = test_client_factory(app)

        response = client.get("/")

        assert response.headers["x-frame-options"] == "SAMEORIGIN"
```
