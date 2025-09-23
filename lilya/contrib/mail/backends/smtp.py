from __future__ import annotations

import smtplib
from collections.abc import Sequence
from email.message import EmailMessage as PyEmailMessage
from email.utils import make_msgid

import anyio

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage as LilyaEmailMessage


def _add_alternative(
    message: PyEmailMessage,
    content: bytes,
    subtype: str,
    maintype: str = "text",
) -> None:
    """
    Add an alternative MIME part to a message (e.g., HTML).
    """
    message.add_alternative(content, subtype=subtype)


async def build_email_message(message: LilyaEmailMessage) -> PyEmailMessage:
    """
    Build a fully-formed RFC-5322 `EmailMessage` suitable for SMTP delivery.

    Handles:
        - Plain text and HTML bodies (with multipart/alternative if both are present).
        - Extra alternatives (e.g., text/calendar).
        - Attachments (both in-memory and file-based).
        - Message headers and reply-to.

    Args:
        message: The :class:`LilyaEmailMessage` to transform.

    Returns:
        A standard library :class:`email.message.EmailMessage` ready to send.
    """
    email_message = PyEmailMessage()
    email_message["Subject"] = message.subject
    if message.from_email:
        email_message["From"] = message.from_email
    if message.to:
        email_message["To"] = ", ".join(message.to)
    if message.cc:
        email_message["Cc"] = ", ".join(message.cc)
    if message.reply_to:
        email_message["Reply-To"] = ", ".join(message.reply_to)

    for header_name, header_value in message.headers.items():
        email_message[header_name] = header_value

    # Body handling
    if message.body_text and message.body_html:
        email_message.set_content(message.body_text)
        _add_alternative(email_message, message.body_html.encode("utf-8"), "html")
    elif message.body_html:
        email_message.add_alternative(message.body_html, subtype="html")
    elif message.body_text:
        email_message.set_content(message.body_text)
    else:
        # Ensure an empty but valid body exists
        email_message.set_content("")

    # Extra alternatives (e.g., text/calendar)
    for media_type, content in message.alternatives:
        content_bytes = content.encode("utf-8") if isinstance(content, str) else content
        maintype, _, subtype = media_type.partition("/")
        if not subtype:
            maintype, subtype = "application", "octet-stream"
        if maintype == "text":
            _add_alternative(email_message, content_bytes, subtype=subtype)
        else:
            email_message.add_attachment(content_bytes, maintype=maintype, subtype=subtype)

    # Attachments (in-memory)
    for filename, blob, mimetype in message.attachments:
        maintype, subtype = (
            mimetype.split("/", 1)
            if mimetype and "/" in mimetype
            else ("application", "octet-stream")
        )
        email_message.add_attachment(
            bytes(blob), maintype=maintype, subtype=subtype, filename=filename
        )

    # Attachments (file paths)
    for path in message.attachment_paths:
        with open(path, "rb") as file:
            data = file.read()
        email_message.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=path.split("/")[-1],
        )

    if "Message-Id" not in email_message:
        email_message["Message-Id"] = make_msgid()

    return email_message


class _SMTPConnection:
    """
    Thin async wrapper around `smtplib.SMTP` with connection reuse.

    Provides safe access from async code via `anyio.to_thread`,
    ensuring that blocking SMTP operations don't block the event loop.
    """

    def __init__(
        self,
        host: str,
        port: int,
        use_tls: bool,
        username: str | None,
        password: str | None,
    ) -> None:
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.username = username
        self.password = password
        self._client: smtplib.SMTP | None = None
        self._lock = anyio.Lock()

    async def open(self) -> None:
        """
        Open a new SMTP connection, reusing it if already open.
        """
        async with self._lock:
            if self._client is not None:
                return

            def _connect() -> smtplib.SMTP:
                client = smtplib.SMTP(self.host, self.port, timeout=30)
                client.ehlo()
                if self.use_tls:
                    client.starttls()
                    client.ehlo()
                if self.username:
                    client.login(self.username, self.password or "")
                return client

            self._client = await anyio.to_thread.run_sync(_connect)

    async def close(self) -> None:
        """
        Gracefully close the SMTP connection.
        """
        async with self._lock:
            if self._client is None:
                return

            def _quit(client: smtplib.SMTP) -> None:
                try:
                    client.quit()
                finally:
                    try:
                        client.close()
                    except Exception:  # noqa
                        ...

            await anyio.to_thread.run_sync(_quit, self._client)
            self._client = None

    async def send(self, email_message: PyEmailMessage, recipients: Sequence[str]) -> None:
        """
        Send a single message through the active SMTP connection.

        Args:
            email_message: The fully-built :class:`EmailMessage` to send.
            recipients: A sequence of email addresses.
        """
        async with self._lock:
            if self._client is None:
                raise RuntimeError("SMTP connection is not open")

            def _sendmail(client: smtplib.SMTP) -> None:
                client.send_message(email_message, to_addrs=list(recipients))

            await anyio.to_thread.run_sync(_sendmail, self._client)


class SMTPBackend(BaseMailBackend):
    """
    Async-friendly SMTP backend with connection reuse.

    Supports:
        - Plain text, HTML, multipart, and attachments.
        - Connection pooling across multiple messages.
        - Optional TLS and authentication.

    Example:
        ```python
        backend = SMTPBackend(
            host="smtp.gmail.com",
            port=587,
            username="me@gmail.com",
            password="secret",
            use_tls=True,
            default_from_email="noreply@myapp.com",
        )
        ```
    """

    def __init__(
        self,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        default_from_email: str | None = None,
    ) -> None:
        self.default_from_email = default_from_email or username
        self._conn = _SMTPConnection(host, port, use_tls, username, password)

    async def open(self) -> None:
        """Open the underlying SMTP connection."""
        await self._conn.open()

    async def close(self) -> None:
        """Close the underlying SMTP connection."""
        await self._conn.close()

    async def send(self, message: LilyaEmailMessage) -> None:
        """
        Send a single email via SMTP.

        Args:
            message: The :class:`LilyaEmailMessage` to deliver.
        """
        if not message.from_email and self.default_from_email:
            message.from_email = self.default_from_email
        email_message = await build_email_message(message)
        await self._conn.send(email_message, message.all_recipients())

    async def send_many(self, messages: Sequence[LilyaEmailMessage]) -> None:
        """
        Send multiple emails efficiently via one open SMTP connection.

        Args:
            messages: A sequence of :class:`LilyaEmailMessage` instances.
        """
        for message in messages:
            if not message.from_email and self.default_from_email:
                message.from_email = self.default_from_email
            email_message = await build_email_message(message)
            await self._conn.send(email_message, message.all_recipients())
