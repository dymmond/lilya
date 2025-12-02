import os

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
