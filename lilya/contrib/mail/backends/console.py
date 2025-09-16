from __future__ import annotations

import sys

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage


class ConsoleBackend(BaseMailBackend):
    """
    Writes emails to stdout for debugging.
    """

    async def send(self, message: EmailMessage) -> None:
        print("====== Email (console) ======", file=sys.stdout)
        print(f"From: {message.from_email}", file=sys.stdout)
        print(f"To: {', '.join(message.to)}", file=sys.stdout)
        if message.cc:
            print(f"Cc: {', '.join(message.cc)}", file=sys.stdout)
        if message.bcc:
            print(f"Bcc: {', '.join(message.bcc)}", file=sys.stdout)
        if message.reply_to:
            print(f"Reply-To: {', '.join(message.reply_to)}", file=sys.stdout)
        print(f"Subject: {message.subject}", file=sys.stdout)
        if message.body_text:
            print("\n-- text/plain --\n" + message.body_text, file=sys.stdout)
        if message.body_html:
            print("\n-- text/html --\n" + message.body_html, file=sys.stdout)
        if message.alternatives:
            print(f"\n-- alternatives -- {len(message.alternatives)} part(s)", file=sys.stdout)
        if message.attachments or message.attachment_paths:
            print(
                f"\n-- attachments -- {len(message.attachments) + len(message.attachment_paths)}",
                file=sys.stdout,
            )
        if message.headers:
            print("\n-- headers --", file=sys.stdout)
            for k, v in message.headers.items():
                print(f"{k}: {v}", file=sys.stdout)
        print("================================", file=sys.stdout)
