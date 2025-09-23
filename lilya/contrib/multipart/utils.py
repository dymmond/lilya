from __future__ import annotations

import re
from urllib.parse import unquote, unquote_to_bytes

# RFC 2616 token and quoted-string grammar
_TOKEN = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_QUOTED = r'"(?:[^"\\]|\\.)*"'
_PARAM = re.compile(rf";\s*({_TOKEN})\s*=\s*({_TOKEN}|{_QUOTED})")


def parse_options_header(header: bytes | str | None) -> tuple[bytes, dict[bytes, bytes]]:
    """
    Parse a Content-Type style header with parameters.

    Examples:
        >>> parse_options_header("multipart/form-data; boundary=abc")
        (b"multipart/form-data", {b"boundary": b"abc"})

    Args:
        header: Raw header string or bytes.

    Returns:
        A tuple ``(main_value, params)`` where:
            - main_value is the lowercased main type as bytes
            - params is a dict of lowercased parameter keys to values (bytes)
    """
    if header is None:
        return b"", {}
    if isinstance(header, str):
        header_bytes = header.encode("latin-1", "ignore")
    else:
        header_bytes = header

    parts = header_bytes.split(b";")
    main_value = parts[0].strip().lower()
    params: dict[bytes, bytes] = {}

    for segment in parts[1:]:
        segment = segment.strip()
        if not segment or b"=" not in segment:
            continue
        key, value = segment.split(b"=", 1)
        key = key.strip().lower()  # keep full key (may end with "*")
        value = value.strip()
        if value.startswith(b'"') and value.endswith(b'"') and len(value) >= 2:
            value = value[1:-1]
        params[key] = value

    return main_value, params


def decode_rfc5987_param(value: str, default_charset: str = "utf-8") -> str:
    """
    Decode a parameter value encoded per RFC 5987 / RFC 2231.

    Format is usually: ``charset''percent-encoded-data``.

    Example:
        >>> decode_rfc5987_param("utf-8''%E6%96%87.txt")
        '文.txt'

    Args:
        value: The encoded string (e.g. from filename* or name*).
        default_charset: Fallback charset if none provided.

    Returns:
        Decoded unicode string.
    """
    try:
        charset, _, encoded = value.partition("''")
        decoded = unquote(encoded)
        return decoded.encode("latin-1", "ignore").decode(charset or default_charset, "replace")
    except Exception:  # noqa
        return unquote(value)


def _decode_rfc5987(raw: bytes, charset: str) -> str:
    """
    Internal helper to decode RFC 5987 parameter values from raw bytes.

    Args:
        raw: Raw value bytes, e.g. b"utf-8''%E6%96%87.txt".
        charset: Fallback charset to use if decoding fails.

    Returns:
        Decoded unicode string.
    """
    try:
        cs, _, encoded = raw.partition(b"''")
        decoded_bytes = unquote_to_bytes(encoded.decode("ascii", "ignore"))
        try:
            if isinstance(cs, bytes):
                charset_name = cs.decode() or charset
            else:
                charset_name = cs or charset  # type: ignore
            return decoded_bytes.decode(charset_name, "replace")
        except Exception:  # noqa
            return decoded_bytes.decode(charset or "utf-8", "replace")
    except Exception:  # noqa
        return unquote(raw.decode("latin-1", "ignore"))
