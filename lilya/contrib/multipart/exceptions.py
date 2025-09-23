class ParseError(Exception):
    """
    Base class for all parsing-related errors in Lilya’s multipart/querystring
    handling system.

    This should not be raised directly; instead, raise one of the more specific
    subclasses depending on the context (decoding, multipart, querystring, etc.).
    """

    ...


class DecodeError(ParseError):
    """
    Raised when a header, parameter, or field value cannot be decoded properly.

    Typical causes:
    - Invalid character encoding in a multipart header (e.g. malformed UTF-8).
    - Unsupported or malformed Content-Transfer-Encoding.
    """

    ...


class FileError(ParseError):
    """
    Raised when an error occurs while handling uploaded file data.

    Examples:
    - Failure to create or write to a temporary file.
    - Exceeding file size limits while streaming data.
    """

    ...


class FormParserError(ParseError):
    """
    Raised when the high-level FormParser cannot be created or executed.

    Examples:
    - Invalid or missing Content-Type headers.
    - Unsupported form encoding (not multipart, urlencoded, or octet-stream).
    """

    ...


class MultipartParseError(ParseError):
    """
    Raised when a multipart/form-data body cannot be parsed successfully.

    Examples:
    - Missing or invalid boundary parameter.
    - Truncated or malformed multipart segments.
    - Exceeding the maximum allowed number of parts or fields.
    """

    ...


class QuerystringParseError(ParseError):
    """
    Raised when a query string or `application/x-www-form-urlencoded`
    body cannot be parsed successfully.

    Examples:
    - Invalid percent-encoding in keys or values.
    - Malformed key/value pairs (missing '=' separator).
    """

    ...
