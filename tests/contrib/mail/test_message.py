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
