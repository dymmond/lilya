# Mail System in Lilya

The `lilya.contrib.mail` module provides a **powerful, async-native email system** built for modern applications.

It’s designed to be lightweight yet as powerful as other’s email framework — but without blocking your event loop.

## What is the Mail System?

The mail system in Lilya is a **pluggable email sending framework**.
It abstracts common tasks like:

* Composing messages with **text, HTML, attachments, headers**.
* Sending via different **backends** (SMTP, Console, File, InMemory).
* Rendering **templates with Jinja2** for transactional emails.
* Supporting **multipart/alternative** emails (plain-text + HTML).
* Allowing custom backends for services like Mailgun, Brevo, or Mailchimp.

---

## Why Use Lilya’s Mail System?

1. **Async-first**: Unlike Django’s sync system, Lilya integrates natively with asyncio/anyio.
2. **Flexible backends**: Choose SMTP, debugging backends, or third-party APIs.
3. **Production-ready**: Connection pooling, batch sending, lifecycle hooks.
4. **Customizable**: Write your own backend for any provider.
5. **Lightweight**: You only import what you need, it’s not tied to ORM or heavy dependencies.

---

## Quick Start

### Configure backend

```python
# configs/development/settings.py
from lilya.contrib.mail.backends.smtp import SMTPBackend

MAIL_BACKEND = SMTPBackend(
    host="smtp.gmail.com",
    port=587,
    username="me@gmail.com",
    password="secret",
    use_tls=True,
    default_from_email="noreply@myapp.com",
)

MAIL_TEMPLATES = "myapp/templates/emails"
```

### Setup in app

```python
from lilya.apps import Lilya
from lilya.contrib.mail.startup import setup_mail
from configs.development import settings

app = Lilya()
setup_mail(app, backend=settings.MAIL_BACKEND, template_dir=settings.MAIL_TEMPLATES)
```

### Send a message

```python
from lilya.contrib.mail import EmailMessage

async def signup_handler(request):
    mailer = request.app.state.mailer
    msg = EmailMessage(
        subject="Welcome!",
        to=["john@example.com"],
        body_text="Hello John, thanks for signing up!",
        body_html="<h1>Hello John 👋</h1><p>Thanks for signing up!</p>",
    )
    await mailer.send(msg)
```

---

## Sending Templated Emails

```python
from lilya.apps import Lilya

app = Lilya()

@app.get("/welcome")
async def send_welcome(request):
    mailer = request.app.state.mailer
    await mailer.send_template(
        template_html="welcome.html",
        context={"name": "John", "product": "Lilya"},
        subject="Welcome to Lilya",
        to=["john@example.com"],
    )
    return {"status": "sent"}
```

### `welcome.html`

```html
<html>
  <body>
    <h1>Hello {{ name }} 👋</h1>
    <p>Welcome to {{ product }}.</p>
  </body>
</html>
```

If no plain-text template is provided, Lilya auto-generates one from the HTML.

---

## Available Backends

### SMTP

The standard backend for production use.

Supports **connection reuse/pooling** for efficiency.

```python
from lilya.contrib.mail.backends.smtp import SMTPBackend

backend = SMTPBackend(
    host="smtp.sendgrid.net",
    port=587,
    username="apikey",
    password="SENDGRID_API_KEY",
    use_tls=True,
)
```

---

### Console

Prints emails to stdout, perfect for development.

```python
from lilya.contrib.mail import Mailer
from lilya.contrib.mail.backends.console import ConsoleBackend

mailer = Mailer(backend=ConsoleBackend())
```

---

### File

Stores emails as `.eml` files.

```python
from lilya.contrib.mail.backends.file import FileBackend

backend = FileBackend(directory="tmp/emails")
```

---

### In-Memory

Stores emails in `backend.outbox`, great for testing.

```python
from lilya.contrib.mail.backends.inmemory import InMemoryBackend

backend = InMemoryBackend()
```

---

## Batch Sending

```python
from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.console import ConsoleBackend

msgs = [
    EmailMessage(subject="One", to=["a@example.com"], body_text="Message one"),
    EmailMessage(subject="Two", to=["b@example.com"], body_text="Message two"),
]


mailer = Mailer(backend=ConsoleBackend())
await mailer.send_many(msgs)
```

---

## Custom Backends

You can integrate **any third-party service** (Mailgun, Brevo, Mailchimp, etc.) by extending `BaseMailBackend`.

### Example: Mailgun Backend

```python
import httpx
from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage

class MailgunBackend(BaseMailBackend):
    def __init__(self, api_key: str, domain: str) -> None:
        self.api_key = api_key
        self.domain = domain

    async def send(self, message: EmailMessage) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.mailgun.net/v3/{self.domain}/messages",
                auth=("api", self.api_key),
                data={
                    "from": message.from_email or f"noreply@{self.domain}",
                    "to": message.to,
                    "subject": message.subject,
                    "text": message.body_text,
                    "html": message.body_html,
                },
            )
```

### Example: Brevo Backend

```python
import httpx
from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage

class BrevoBackend(BaseMailBackend):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def send(self, message: EmailMessage) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": self.api_key},
                json={
                    "sender": {"email": message.from_email or "noreply@myapp.com"},
                    "to": [{"email": r} for r in message.to],
                    "subject": message.subject,
                    "textContent": message.body_text,
                    "htmlContent": message.body_html,
                },
            )
```

### Example: Mailchimp Transactional (Mandrill)

```python
import httpx
from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage

class MailchimpBackend(BaseMailBackend):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def send(self, message: EmailMessage) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://mandrillapp.com/api/1.0/messages/send.json",
                json={
                    "key": self.api_key,
                    "message": {
                        "from_email": message.from_email,
                        "subject": message.subject,
                        "text": message.body_text,
                        "html": message.body_html,
                        "to": [{"email": r, "type": "to"} for r in message.to],
                    },
                },
            )
```

---

## Best Practices

* Always configure a **default from email** (`noreply@...`) in production.
* Use **HTML + text multipart** to avoid spam filters.
* In dev, prefer **ConsoleBackend** or **FileBackend**.
* For tests, use **InMemoryBackend** and assert on `.outbox`.
* For production, use **SMTPBackend** or a **custom API backend**.
* Keep **transactional templates** in a dedicated directory (`templates/emails/`).

---

## Summary

* `EmailMessage`: Describes what to send.
* `Mailer`: Coordinates sending, templating, batching.
* `BaseMailBackend`: Pluggable backends (SMTP, Console, File, InMemory).
* **Custom backends**: Easy integration with services like Mailgun, Brevo, Mailchimp, etc.

With these tools, Lilya’s mail system is **powerful**, but async-native, lighter, and more flexible.
