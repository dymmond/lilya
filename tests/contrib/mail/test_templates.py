import tempfile

from lilya.contrib.mail.templates import TemplateRenderer


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
