from __future__ import annotations

import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _html_to_text_simple(html: str) -> str:
    """
    Minimal HTML->text fallback (keeps it dependency-free).
    Good enough for simple transactional emails.
    """
    # Replace breaks and paragraphs with newlines
    html = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</\s*p\s*>", "\n\n", html, flags=re.I)

    # Strip tags
    text = re.sub(r"<[^>]+>", "", html)

    # Collapse whitespace
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


class TemplateRenderer:
    def __init__(self, template_dir: str) -> None:
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,
        )

    def render_html(self, template_name: str, context: dict[str, Any]) -> str:
        return self.env.get_template(template_name).render(**context)

    def render_pair(
        self,
        template_html: str,
        context: dict[str, Any],
        template_text: str | None = None,
    ) -> tuple[str, str]:
        html = self.render_html(template_html, context)
        if template_text:
            text = self.env.get_template(template_text).render(**context)
        else:
            text = _html_to_text_simple(html)
        return text, html
