import pytest

from lilya.apps import Lilya
from lilya.contrib.mail import EmailMessage
from lilya.contrib.mail.backends.inmemory import InMemoryBackend
from lilya.contrib.mail.dependencies import Mail
from lilya.contrib.mail.mailer import Mailer
from lilya.contrib.mail.startup import setup_mail
from lilya.dependencies import Provide
from lilya.testclient import TestClient

pytestmark = pytest.mark.asyncio


async def test_mail_dependency_injection(tmp_path, test_client_factory):
    backend = InMemoryBackend()
    app = Lilya()

    # Attach mailer to app
    setup_mail(app, backend=backend, template_dir=str(tmp_path))

    @app.post("/send", dependencies={"mailer": Mail})
    async def send_email(mailer: Mail):
        msg = EmailMessage(subject="Hello", to=["a@test"], body_text="hi")
        await mailer.send(msg)
        return {"ok": True}

    client = TestClient(app)

    # Call endpoint
    response = client.post("/send")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Ensure message was delivered through backend
    assert len(backend.outbox) == 1
    assert backend.outbox[0].subject == "Hello"
    assert backend.outbox[0].body_text == "hi"
    assert backend.outbox[0].to == ["a@test"]


async def test_mail_dependency_without_setup_raises(test_client_factory):
    app = Lilya()

    @app.get("/test", dependencies={"mailer": Mail})
    async def test_handler(mailer: Mail):
        return {"ok": True}

    client = TestClient(app)

    # No setup_mail called -> should raise RuntimeError
    with pytest.raises(RuntimeError):
        client.get("/test")


async def test_mail_dependency_reuses_same_instance(tmp_path):
    backend = InMemoryBackend()
    app = Lilya()

    # Attach mailer to app
    setup_mail(app, backend=backend, template_dir=str(tmp_path))

    calls: list[Mailer] = []

    @app.get("/ping", dependencies={"mailer": Mail})
    async def ping(mailer: Mail):
        calls.append(mailer)
        return {"ok": True}

    client = TestClient(app)

    # Call twice
    client.get("/ping")
    client.get("/ping")

    assert len(calls) == 2

    # Both injections should resolve to the same Mailer instance
    assert calls[0] is calls[1]
    assert isinstance(calls[0], Mailer)


async def test_mail_dependency_override(tmp_path):
    backend = InMemoryBackend()
    app = Lilya()

    setup_mail(app, backend=backend, template_dir=str(tmp_path))

    class FakeMailer:
        def __init__(self):
            self.sent = []

        async def send(self, message: EmailMessage):
            self.sent.append(message)

    fake_mailer = FakeMailer()

    async def _resolve_fake(request, **kwargs):
        return fake_mailer

    FakeMail = Provide(_resolve_fake)

    @app.post("/send", dependencies={"mailer": FakeMail})
    async def send_email(mailer: Mail):
        msg = EmailMessage(subject="fake", to=["x@test"], body_text="hi")
        await mailer.send(msg)
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/send")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    assert len(fake_mailer.sent) == 1
    assert fake_mailer.sent[0].subject == "fake"


async def test_mail_dependency_misconfigured_state(tmp_path):
    app = Lilya()
    # Deliberately attach wrong object
    app.state.mailer = object()

    @app.get("/bad", dependencies={"mailer": Mail})
    async def bad(mailer: Mail):
        return {"ok": True}

    client = TestClient(app)

    with pytest.raises(RuntimeError):
        client.get("/bad")
