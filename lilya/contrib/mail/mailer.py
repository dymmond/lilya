from __future__ import annotations

from collections.abc import Sequence

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.exceptions import BackendNotConfigured
from lilya.contrib.mail.message import EmailMessage
from lilya.contrib.mail.templates import TemplateRenderer


class Mailer:
    """
    High-level API with:
      - send / send_many
      - send_template (html+auto-text)
      - optional TemplateRenderer
    """

    def __init__(
        self, backend: BaseMailBackend | None = None, template_dir: str | None = None
    ) -> None:
        self.backend = backend
        self.templates = TemplateRenderer(template_dir) if template_dir else None

    async def open(self) -> None:
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        await self.backend.open()

    async def close(self) -> None:
        if self.backend:
            await self.backend.close()

    async def send(self, message: EmailMessage) -> None:
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        if not (
            message.body_text
            or message.body_html
            or message.alternatives
            or message.attachments
            or message.attachment_paths
        ):
            # Allow empty body but warn by raising InvalidMessage if truly empty and no parts
            pass
        await self.backend.send(message)

    async def send_many(self, messages: Sequence[EmailMessage]) -> None:
        if not self.backend:
            raise BackendNotConfigured("No mail backend configured.")
        await self.backend.send_many(messages)

    async def send_template(
        self,
        *,
        template_html: str,
        context: dict,
        subject: str,
        to: list[str],
        from_email: str | None = None,
        template_text: str | None = None,
        reply_to: list[str] | None = None,
        headers: dict | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list | None = None,
        attachment_paths: list[str] | None = None,
    ) -> None:
        if not self.templates:
            raise BackendNotConfigured("No template renderer configured.")
        text, html = self.templates.render_pair(
            template_html, context, template_text=template_text
        )

        msg = EmailMessage(
            subject=subject,
            to=to,
            from_email=from_email,
            body_text=text,
            body_html=html,
            reply_to=reply_to or [],
            headers=headers or {},
            cc=cc or [],
            bcc=bcc or [],
            attachments=attachments or [],
            attachment_paths=attachment_paths or [],
        )
        await self.send(msg)
