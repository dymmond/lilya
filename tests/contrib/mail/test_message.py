import asyncio

from lilya.contrib.mail.backends.file import FileBackend
from lilya.contrib.mail.message import EmailMessage


def test_all_recipients():
    msg = EmailMessage(
        subject="hi",
        to=["a@example.com"],
        cc=["b@example.com"],
        bcc=["c@example.com"],
    )
    assert sorted(msg.all_recipients()) == ["a@example.com", "b@example.com", "c@example.com"]


def test_attachments_in_memory():
    msg = EmailMessage(
        subject="File",
        to=["x@example.com"],
        attachments=[("hello.txt", b"hello world", "text/plain")],
    )
    assert msg.attachments[0][0] == "hello.txt"


def test_attachments_file_path(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hi")
    msg = EmailMessage(subject="File", to=["x@example.com"], attachment_paths=[str(file_path)])
    assert str(file_path) in msg.attachment_paths


def test_headers_preserved():
    msg = EmailMessage(
        subject="HeaderTest",
        to=["a@example.com"],
        body_text="hi",
        headers={"X-Test": "123", "X-Env": "staging"},
    )
    assert msg.headers["X-Test"] == "123"
    assert "X-Env" in msg.headers


def test_meta_does_not_affect_recipients():
    msg = EmailMessage(
        subject="MetaTest",
        to=["a@example.com"],
        body_text="hi",
        meta={"tracking_id": "abc123"},
    )
    assert msg.meta["tracking_id"] == "abc123"
    assert msg.all_recipients() == ["a@example.com"]


def test_empty_subject_fallback_for_filebackend(tmp_path):
    msg = EmailMessage(subject="", to=["a@example.com"], body_text="hi")

    backend = FileBackend(directory=str(tmp_path))

    asyncio.run(backend.open())
    asyncio.run(backend.send(msg))
    files = list(tmp_path.glob("*.eml"))

    assert files
    assert "no-subject" in files[0].name


def test_alternatives():
    msg = EmailMessage(
        subject="Alt",
        to=["a@test"],
        body_text="Plain",
        alternatives=[("text/calendar", "BEGIN:VCALENDAR\nEND:VCALENDAR")],
    )

    assert msg.alternatives

    media_type, content = msg.alternatives[0]

    assert media_type == "text/calendar"
    assert "VCALENDAR" in content
