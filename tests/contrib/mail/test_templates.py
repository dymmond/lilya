import tempfile

import pytest
from jinja2.exceptions import TemplateNotFound

from lilya.contrib.mail.templates import TemplateRenderer, _html_to_text_simple


def test_render_html_and_text():
    tmpdir = tempfile.mkdtemp()
    html_file = f"{tmpdir}/welcome.html"
    with open(html_file, "w") as f:
        f.write("<p>Hello {{ name }}</p>")

    renderer = TemplateRenderer(tmpdir)
    html = renderer.render_html("welcome.html", {"name": "John"})

    assert "John" in html

    text, html = renderer.render_pair("welcome.html", {"name": "Jane"})

    assert "Jane" in text
    assert "Jane" in html


def test_html_to_text_simple_handles_breaks_and_paragraphs():
    html = "<p>Hello<br>World</p>"
    text = _html_to_text_simple(html)

    assert "Hello" in text
    assert "World" in text
    assert "\n" in text  # linebreak inserted


def test_render_invalid_template_raises(tmp_path):
    renderer = TemplateRenderer(str(tmp_path))

    with pytest.raises(TemplateNotFound):
        renderer.render_html("nonexistent.html", {})
