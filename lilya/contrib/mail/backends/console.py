from __future__ import annotations

import sys

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage


class ConsoleBackend(BaseMailBackend):
    """
    A mail backend that writes emails to standard output.

    This backend is intended for **development and debugging**.
    Instead of actually sending messages, it prints them to `stdout`
    in a structured format.

    Typical usage:
        ```python
        backend = ConsoleBackend()
        mailer = Mailer(backend=backend)
        await mailer.send(EmailMessage(...))
        ```
    """

    async def send(self, message: EmailMessage) -> None:
        """
        Print an email message to stdout.

        Args:
            message: The :class:`EmailMessage` instance to display.

        Notes:
            - This backend does not perform any validation beyond
              what `EmailMessage` provides.
            - It does not persist or deliver the message anywhere.
        """
        print("====== Email (console) ======", file=sys.stdout)

        # Basic headers
        print(f"From: {message.from_email}", file=sys.stdout)
        print(f"To: {', '.join(message.to)}", file=sys.stdout)

        if message.cc:
            print(f"Cc: {', '.join(message.cc)}", file=sys.stdout)
        if message.bcc:
            print(f"Bcc: {', '.join(message.bcc)}", file=sys.stdout)
        if message.reply_to:
            print(f"Reply-To: {', '.join(message.reply_to)}", file=sys.stdout)

        print(f"Subject: {message.subject}", file=sys.stdout)

        # Body sections
        if message.body_text:
            print("\n-- text/plain --\n" + message.body_text, file=sys.stdout)
        if message.body_html:
            print("\n-- text/html --\n" + message.body_html, file=sys.stdout)
        if message.alternatives:
            print(
                f"\n-- alternatives -- ({len(message.alternatives)} part(s))",
                file=sys.stdout,
            )

        # Attachments
        if message.attachments or message.attachment_paths:
            attachment_count = len(message.attachments) + len(message.attachment_paths)
            print(f"\n-- attachments -- ({attachment_count})", file=sys.stdout)

        # Extra headers
        if message.headers:
            print("\n-- headers --", file=sys.stdout)
            for header_name, header_value in message.headers.items():
                print(f"{header_name}: {header_value}", file=sys.stdout)

        print("================================", file=sys.stdout)
