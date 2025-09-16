class MailError(Exception):
    """
    Base exception for all mail-related errors in Lilya.

    All other exceptions in the mail contrib system inherit from this,
    making it easy to catch or filter mail-specific errors.
    """

    ...


class BackendNotConfigured(MailError):
    """
    Raised when a mail operation is attempted without a configured backend.

    Example:
        ```python
        mailer = Mailer()
        await mailer.send(EmailMessage(...))  # raises BackendNotConfigured
        ```
    """

    ...


class InvalidMessage(MailError):
    """
    Raised when an `EmailMessage` is structurally invalid or incomplete.

    Typical causes:
        - Missing recipients (`to`, `cc`, or `bcc`).
        - No body content (text, HTML, or alternatives).
        - Malformed attachments.

    Example:
        ```python
        msg = EmailMessage(subject="Empty", to=[])
        await mailer.send(msg)  # raises InvalidMessage
        ```
    """

    ...
