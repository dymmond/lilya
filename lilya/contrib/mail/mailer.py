from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.exceptions import BackendNotConfigured, InvalidMessage
from lilya.contrib.mail.message import EmailMessage
from lilya.contrib.mail.templates import TemplateRenderer


class Mailer:
    """
    High-level API for sending emails.

    This class wraps a configured mail backend (e.g. SMTP, console,
    file, in-memory) and optionally integrates with Jinja2 templates.

    Features:
        - :meth:`send`: send a single email message.
        - :meth:`send_many`: send multiple messages efficiently.
        - :meth:`send_template`: render and send a Jinja2-based template.
        - Lifecycle support (:meth:`open`, :meth:`close`) for connection pooling.

    Example:
        ```python
        backend = SMTPBackend(...)
        mailer = Mailer(backend=backend, template_dir="templates/emails")

        message = EmailMessage(
            subject="Welcome",
            to=["user@example.com"],
            body_text="Hello!",
        )

        await mailer.send(message)
        ```
    """

    def __init__(
        self, backend: BaseMailBackend | None = None, template_dir: str | None = None
    ) -> None:
        """
        Initialize a Mailer instance.

        Args:
            backend: The mail backend used to send messages.
            template_dir: Optional directory path containing Jinja2 templates.
        """
        self.backend = backend
        self.templates = TemplateRenderer(template_dir) if template_dir else None

    async def open(self) -> None:
        """
        Open the mail backend connection, if supported.

        Raises:
            BackendNotConfigured: If no backend is configured.
        """
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        await self.backend.open()

    async def close(self) -> None:
        """
        Close the mail backend connection, if supported.
        """
        if self.backend:
            await self.backend.close()

    async def send(self, message: EmailMessage) -> None:
        """
        Send a single email message.

        Args:
            message: The email to be sent.

        Raises:
            BackendNotConfigured: If no backend is configured.
        """
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        if not message.all_recipients():
            raise InvalidMessage("No recipients specified.")
        if not (
            message.body_text
            or message.body_html
            or message.alternatives
            or message.attachments
            or message.attachment_paths
        ):
            raise InvalidMessage("Message must have at least one body part or attachment.")
        await self.backend.send(message)

    async def send_many(self, messages: Sequence[EmailMessage]) -> None:
        """
        Send multiple email messages.

        Args:
            messages: A sequence of `EmailMessage` instances.

        Raises:
            BackendNotConfigured: If no backend is configured.
        """
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        await self.backend.send_many(messages)

    async def send_template(
        self,
        *,
        template_html: str,
        context: dict[str, Any],
        subject: str,
        to: list[str],
        from_email: str | None = None,
        template_text: str | None = None,
        reply_to: list[str] | None = None,
        headers: dict[str, str] | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list | None = None,
        attachment_paths: list[str] | None = None,
    ) -> None:
        """
        Render a Jinja2 template and send it as an email.

        If no plain-text template is provided, a fallback is automatically
        generated from the rendered HTML.

        Args:
            template_html: Filename of the HTML template.
            context: Dictionary of variables for rendering.
            subject: Email subject line.
            to: List of recipient addresses.
            from_email: Optional sender address. If omitted, backend default is used.
            template_text: Optional filename of a plain-text template.
            reply_to: Optional list of reply-to addresses.
            headers: Optional dictionary of extra headers.
            cc: Optional list of CC recipients.
            bcc: Optional list of BCC recipients.
            attachments: Optional list of in-memory attachments.
            attachment_paths: Optional list of file paths for attachments.

        Raises:
            BackendNotConfigured: If no template renderer is configured.
        """
        if not self.templates:
            raise BackendNotConfigured("No template renderer configured.")

        text_body, html_body = self.templates.render_pair(
            template_html, context, template_text=template_text
        )

        message = EmailMessage(
            subject=subject,
            to=to,
            from_email=from_email,
            body_text=text_body,
            body_html=html_body,
            reply_to=reply_to or [],
            headers=headers or {},
            cc=cc or [],
            bcc=bcc or [],
            attachments=attachments or [],
            attachment_paths=attachment_paths or [],
        )
        await self.send(message)
