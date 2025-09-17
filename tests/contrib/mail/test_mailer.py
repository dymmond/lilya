import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.inmemory import InMemoryBackend
from lilya.contrib.mail.exceptions import BackendNotConfigured, InvalidMessage

pytestmark = pytest.mark.anyio


async def test_send_requires_backend():
    mailer = Mailer()
    msg = EmailMessage(subject="test", to=["a@b.com"], body_text="hi")

    with pytest.raises(BackendNotConfigured):
        await mailer.send(msg)


async def test_send_inmemory_backend():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)
    msg = EmailMessage(subject="test", to=["a@b.com"], body_text="hi")

    await mailer.send(msg)

    assert len(backend.outbox) == 1
    assert backend.outbox[0].body_text == "hi"


async def test_send_many():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)
    msgs = [
        EmailMessage(subject="one", to=["1@test"], body_text="1"),
        EmailMessage(subject="two", to=["2@test"], body_text="2"),
    ]

    await mailer.send_many(msgs)

    assert len(backend.outbox) == 2


async def test_invalid_message_no_body_or_recipients():
    mailer = Mailer(backend=InMemoryBackend())
    msg = EmailMessage(subject="Empty", to=[], body_text=None, body_html=None)

    with pytest.raises(InvalidMessage):
        await mailer.send(msg)


async def test_open_close_idempotent():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)
    await mailer.open()
    await mailer.open()  # second call should not error
    await mailer.close()
    await mailer.close()  # second call should not error


async def test_send_template_html_and_text(tmp_path):
    template_dir = tmp_path
    html_file = template_dir / "welcome.html"
    text_file = template_dir / "welcome.txt"
    html_file.write_text("<h1>Hello {{ name }}</h1>")
    text_file.write_text("Hello {{ name }}")

    backend = InMemoryBackend()
    mailer = Mailer(backend=backend, template_dir=str(template_dir))

    await mailer.send_template(
        template_html="welcome.html",
        template_text="welcome.txt",
        context={"name": "John"},
        subject="Welcome",
        to=["a@example.com"],
    )

    assert backend.outbox
    assert "John" in backend.outbox[0].body_text
    assert "John" in backend.outbox[0].body_html


async def test_send_template_without_renderer_raises():
    mailer = Mailer(backend=InMemoryBackend())

    with pytest.raises(BackendNotConfigured):
        await mailer.send_template(
            template_html="x.html",
            context={},
            subject="test",
            to=["a@example.com"],
        )


async def test_headers_reply_to_cc_bcc_preserved():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)

    msg = EmailMessage(
        subject="hdrs",
        to=["a@test"],
        cc=["b@test"],
        bcc=["c@test"],
        reply_to=["reply@test"],
        body_text="hi",
        headers={"X-Custom": "123"},
    )

    await mailer.send(msg)

    stored = backend.outbox[0]

    assert stored.cc == ["b@test"]
    assert stored.bcc == ["c@test"]
    assert stored.reply_to == ["reply@test"]
    assert stored.headers["X-Custom"] == "123"
