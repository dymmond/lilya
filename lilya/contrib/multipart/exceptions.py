class ParseError(Exception):
    """Base error for parsing problems."""
    ...


class DecodeError(ParseError):
    """Raised when a header or value cannot be decoded."""
    ...


class FileError(ParseError):
    """Raised for file I/O issues while handling uploads."""
    ...


class FormParserError(ParseError):
    """Raised when FormParser cannot be constructed or run."""
    ...


class MultipartParseError(ParseError):
    """Raised for errors while parsing multipart bodies."""
    ...


class QuerystringParseError(ParseError):
    """Raised for errors while parsing query strings / x-www-form-urlencoded bodies."""
    ...
