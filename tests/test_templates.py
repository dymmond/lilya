import os
import pathlib
from unittest import mock

import jinja2
import pytest

from lilya.apps import Lilya
from lilya.background import Task
from lilya.routing import Path
from lilya.templating.jinja import Jinja2Template


@pytest.mark.parametrize("apostrophe", ["'", '"'])
def test_templates(tmpdir, test_client_factory, apostrophe):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write(
            "<html>Hello, <a href='{{ url_for('homepage') }}'>world</a></html>".replace(
                "'", apostrophe
            )
        )

    async def homepage(request):
        return templates.get_template_response(request, "index.html")

    app = Lilya(
        debug=True,
        routes=[Path("/", handler=homepage)],
    )
    templates: Jinja2Template = Jinja2Template(directory=str(tmpdir))

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "<html>Hello, <a href='http://testserver/'>world</a></html>".replace(
        "'", apostrophe
    )
    assert response.template.name == "index.html"
    assert set(response.context.keys()) == {"request"}


def test_async_templates(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("<html>Hello {{ async_fn() }}</html>")

    async def async_fn():
        return "world"

    async def homepage(request):
        return templates.get_template_response(
            request, "index.html", context={"async_fn": async_fn}
        )

    app = Lilya(
        debug=True,
        routes=[Path("/", handler=homepage)],
    )
    templates: Jinja2Template = Jinja2Template(directory=str(tmpdir), enable_async=True)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "<html>Hello world</html>"
    assert response.template.name == "index.html"
    assert set(response.context.keys()) == {"request", "async_fn"}


def test_calls_context_processors(tmp_path, test_client_factory):
    path = tmp_path / "index.html"
    path.write_text("<html>Hello {{ username }}</html>")

    async def homepage(request):
        return templates.get_template_response(request, "index.html")

    def hello_world_processor(request):
        return {"username": "World"}

    app = Lilya(
        debug=True,
        routes=[Path("/", handler=homepage)],
    )
    templates = Jinja2Template(
        directory=tmp_path,
        context_processors=[
            hello_world_processor,
        ],
    )

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "<html>Hello World</html>"
    assert response.template.name == "index.html"
    assert set(response.context.keys()) == {"request", "username"}


# def test_template_with_middleware(tmpdir, test_client_factory):
#     path = os.path.join(tmpdir, "index.html")
#     with open(path, "w") as file:
#         file.write("<html>Hello, <a href='{{ url_for('homepage') }}'>world</a></html>")

#     async def homepage(request):
#         return templates.get_template_response(request, "index.html")

#     class CustomMiddleware(BaseHTTPMiddleware):
#         async def dispatch(self, request, call_next):
#             return await call_next(request)

#     app = Lilya(
#         debug=True,
#         routes=[Path("/", handler=homepage)],
#         middleware=[DefineMiddleware(CustomMiddleware)],
#     )
#     templates = Jinja2Template(directory=str(tmpdir))

#     client = test_client_factory(app)
#     response = client.get("/")
#     assert response.text == "<html>Hello, <a href='http://testserver/'>world</a></html>"
#     assert response.template.name == "index.html"
#     assert set(response.context.keys()) == {"request"}


def test_templates_with_directories(tmp_path: pathlib.Path, test_client_factory):
    dir_a = tmp_path.resolve() / "a"
    dir_a.mkdir()
    template_a = dir_a / "template_a.html"
    template_a.write_text("<html><a href='{{ url_for('page_a') }}'></a> a</html>")

    async def page_a(request):
        return templates.get_template_response(request, "template_a.html")

    dir_b = tmp_path.resolve() / "b"
    dir_b.mkdir()
    template_b = dir_b / "template_b.html"
    template_b.write_text("<html><a href='{{ url_for('page_b') }}'></a> b</html>")

    async def page_b(request):
        return templates.get_template_response(request, "template_b.html")

    app = Lilya(
        debug=True,
        routes=[Path("/a", handler=page_a), Path("/b", handler=page_b)],
    )

    templates = Jinja2Template(directory=[dir_a, dir_b])

    client = test_client_factory(app)
    response = client.get("/a")
    assert response.text == "<html><a href='http://testserver/a'></a> a</html>"
    assert response.template.name == "template_a.html"
    assert set(response.context.keys()) == {"request"}

    response = client.get("/b")
    assert response.text == "<html><a href='http://testserver/b'></a> b</html>"
    assert response.template.name == "template_b.html"
    assert set(response.context.keys()) == {"request"}


def test_templates_require_directory_or_environment():
    with pytest.raises(
        AssertionError, match="either 'env' or 'directory' arguments must be passed but not both."
    ):
        Jinja2Template()  # type: ignore[call-overload]


def test_templates_with_directory(tmpdir):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("Hello")

    templates = Jinja2Template(directory=str(tmpdir))
    template = templates.get_template("index.html")
    assert template.render({}) == "Hello"


def test_templates_with_environment(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("<html>Hello, <a href='{{ url_for('homepage') }}'>world</a></html>")

    async def homepage(request):
        return templates.get_template_response(request, "index.html")

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tmpdir)))
    app = Lilya(
        debug=True,
        routes=[Path("/", handler=homepage)],
    )
    templates = Jinja2Template(env=env)
    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "<html>Hello, <a href='http://testserver/'>world</a></html>"
    assert response.template.name == "index.html"
    assert set(response.context.keys()) == {"request"}


def test_templates_with_kwargs_only(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("value: {{ a }}")
    templates = Jinja2Template(directory=str(tmpdir))

    spy = mock.MagicMock()

    def page(request):
        return templates.get_template_response(
            request=request,
            name="index.html",
            context={"a": "b"},
            status_code=201,
            headers={"x-key": "value"},
            media_type="text/plain",
            background=Task(func=spy),
        )

    app = Lilya(routes=[Path("/", page)])
    client = test_client_factory(app)
    response = client.get("/")

    assert response.text == "value: b"  # context was rendered
    assert response.status_code == 201
    assert response.headers["x-key"] == "value"
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    spy.assert_called()


def test_templates_with_kwargs_only_requires_request_in_context(tmpdir):
    templates = Jinja2Template(directory=str(tmpdir))

    with pytest.raises(AssertionError):
        templates.get_template_response(name="index.html", context={"a": "b"})
