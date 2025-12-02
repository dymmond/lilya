import os
import sys

from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path
from lilya.templating.controllers import TemplateController
from lilya.templating.jinja import Jinja2Template


def test_controller_context_processors(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ greeting }}</p>")

    def greet(request):
        return {"greeting": "Hello"}

    class MyView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [greet]

        async def get(self, request: Request):
            return await self.render_template(request)

    app = Lilya(routes=[Path("/", handler=MyView)])
    client = test_client_factory(app)
    resp = client.get("/")

    assert resp.text == "<p>Hello</p>"
    assert set(resp.context.keys()) == {"request", "greeting"}


def test_context_processors_inheritance(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ base }} {{ child }}</p>")

    def base_proc(request):
        return {"base": "BASE"}

    def child_proc(request):
        return {"child": "CHILD"}

    class BaseView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [base_proc]

    class ChildView(BaseView):
        context_processors = BaseView.context_processors + [child_proc]

        async def get(self, request: Request):
            return await self.render_template(request)

    app = Lilya(routes=[Path("/", handler=ChildView)])
    client = test_client_factory(app)
    resp = client.get("/")

    assert resp.text == "<p>BASE CHILD</p>"
    assert set(resp.context.keys()) == {"request", "base", "child"}


def test_async_context_processor(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ async_value }}</p>")

    async def async_proc(request):
        return {"async_value": "ASYNC"}

    class AsyncView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [async_proc]

        async def get(self, request: Request):
            return await self.render_template(request)

    app = Lilya(routes=[Path("/", handler=AsyncView)])
    client = test_client_factory(app)
    resp = client.get("/")

    assert resp.text == "<p>ASYNC</p>"
    assert set(resp.context.keys()) == {"request", "async_value"}


def test_context_processors_override_context(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ value }}</p>")

    def proc(request):
        return {"value": "processor"}

    class OverrideView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [proc]

        async def get(self, request: Request):
            return await self.render_template(request, {"value": "explicit"})

    app = Lilya(routes=[Path("/", handler=OverrideView)])
    client = test_client_factory(app)
    resp = client.get("/")

    # explicit context wins
    assert resp.text == "<p>explicit</p>"
    assert set(resp.context.keys()) == {"request", "value"}


def test_context_processors_do_not_leak_between_views(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ value|default('none') }}</p>")

    def proc(request):
        return {"value": "A"}

    class AView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [proc]

        async def get(self, request: Request):
            return await self.render_template(request)

    class BView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"

        async def get(self, request: Request):
            return await self.render_template(request)

    app = Lilya(
        routes=[
            Path("/a", handler=AView),
            Path("/b", handler=BView),
        ]
    )

    client = test_client_factory(app)

    resp_a = client.get("/a")
    assert resp_a.text == "<p>A</p>"

    resp_b = client.get("/b")
    assert resp_b.text == "<p>none</p>"  # no leakage


def test_context_processor_dotted_path(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ greeting }}</p>")

    # create module file for dotted import
    module_path = os.path.join(tmpdir, "modctx.py")
    with open(module_path, "w") as f:
        f.write("def greet(request):\n    return {'greeting': 'Hi'}\n")

    class DotView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = ["modctx.greet"]

        async def get(self, request: Request):
            return await self.render_template(request)

    sys.path.insert(0, str(tmpdir))

    app = Lilya(routes=[Path("/", handler=DotView)])
    client = test_client_factory(app)
    resp = client.get("/")

    assert resp.text == "<p>Hi</p>"
    assert set(resp.context.keys()) == {"request", "greeting"}


def test_context_processor_arbitrary_params(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>{{ combo }}</p>")

    def proc(request, controller, custom):
        return {"combo": f"{request.method}-{controller.__class__.__name__}-{custom}"}

    class MyView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [proc]

        async def get(self, request: Request):
            return await self.render_template(request, {"custom": "X"})

    app = Lilya(routes=[Path("/", handler=MyView)])
    client = test_client_factory(app)
    resp = client.get("/")

    assert resp.text == "<p>GET-MyView-X</p>"
    assert set(resp.context.keys()) == {"request", "custom", "combo"}


def test_context_processor_missing_required_param_strict(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as f:
        f.write("<p>x</p>")

    def bad(request, missing):
        return {"oops": True}

    class BadView(TemplateController):
        templates = Jinja2Template(directory=str(tmpdir))
        template_name = "index.html"
        context_processors = [bad]

        async def get(self, request: Request):
            return await self.render_template(request)

    app = Lilya(routes=[Path("/", handler=BadView)])
    client = test_client_factory(app, raise_server_exceptions=True)

    resp = client.get("/")
    assert resp.status_code == 500
    assert "requires unknown parameter" in resp.text
