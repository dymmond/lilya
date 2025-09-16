import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.inmemory import InMemoryBackend
from lilya.contrib.mail.exceptions import BackendNotConfigured

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
