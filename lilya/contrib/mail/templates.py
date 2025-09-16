from __future__ import annotations

import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _html_to_text_simple(html: str) -> str:
    """
    Convert a block of HTML into a minimal plain-text fallback.

    This keeps the mail contrib system dependency-free by avoiding
    external HTML-to-text libraries while still providing a readable
    plain-text version for multipart emails.

    - `<br>` tags are converted into line breaks.
    - `</p>` tags are converted into paragraph breaks.
    - All other HTML tags are stripped.
    - Whitespace is normalized.

    Args:
        html: The raw HTML string.

    Returns:
        A plain text version of the HTML content, suitable for
        inclusion in `EmailMessage.body_text` or multipart emails.
    """
    # Replace breaks and paragraphs with newlines
    html = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</\s*p\s*>", "\n\n", html, flags=re.I)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", html)

    # Collapse excessive whitespace
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)

    return text.strip()


class TemplateRenderer:
    """
    A simple wrapper around Jinja2 to render email templates.

    This allows developers to store transactional email templates
    (HTML and optionally plain-text) in a directory and render them
    with context values before sending.

    Example:
        ```python
        renderer = TemplateRenderer("templates/emails")
        html = renderer.render_html("welcome.html", {"user": "John"})
        text, html = renderer.render_pair("welcome.html", {"user": "John"})
        ```
    """

    def __init__(self, template_dir: str) -> None:
        """
        Initialize a Jinja2 environment for email templates.

        Args:
            template_dir: Path to the directory containing your email templates.
        """
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,
        )

    def render_html(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a single HTML template into a string.

        Args:
            template_name: The filename of the HTML template (e.g. "welcome.html").
            context: A dictionary of variables to pass to the template.

        Returns:
            The rendered HTML string.
        """
        return self.env.get_template(template_name).render(**context)

    def render_pair(
        self,
        template_html: str,
        context: dict[str, Any],
        template_text: str | None = None,
    ) -> tuple[str, str]:
        """
        Render a pair of templates for multipart emails.

        If only an HTML template is provided, a plain-text fallback
        will be auto-generated from the HTML. If a separate text
        template is provided, it will be rendered directly.

        Args:
            template_html: Filename of the HTML template.
            context: Dictionary of variables to pass to the template.
            template_text: Optional filename of a plain-text template.

        Returns:
            A `(text, html)` tuple containing both the plain-text and
            HTML versions of the email body.
        """
        html = self.render_html(template_html, context)
        if template_text:
            text = self.env.get_template(template_text).render(**context)
        else:
            text = _html_to_text_simple(html)
        return text, html
