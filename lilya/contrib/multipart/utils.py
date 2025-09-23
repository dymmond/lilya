from __future__ import annotations

import logging
import re
from urllib.parse import unquote, unquote_to_bytes

logger = logging.getLogger(__name__)

_TOKEN = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_QUOTED = r'"(?:[^"\\]|\\.)*"'
_PARAM = re.compile(rf";\s*({_TOKEN})\s*=\s*({_TOKEN}|{_QUOTED})")


def parse_options_header(header: bytes | str) -> tuple[bytes, dict[bytes, bytes]]:
    if header is None:
        return b"", {}
    if isinstance(header, str):
        header_bytes = header.encode("latin-1", "ignore")
    else:
        header_bytes = header
    parts = header_bytes.split(b";")
    main = parts[0].strip().lower()
    params: dict[bytes, bytes] = {}
    for seg in parts[1:]:
        seg = seg.strip()
        if not seg or b"=" not in seg:
            continue
        k, v = seg.split(b"=", 1)
        k = k.strip().lower()  # ✅ keep the full key, including "*"
        v = v.strip()
        if v.startswith(b'"') and v.endswith(b'"') and len(v) >= 2:
            v = v[1:-1]
        params[k] = v
    return main, params


def decode_rfc5987_param(value: str, default_charset: str = "utf-8") -> str:
    """Decode a RFC 5987/2231 parameter value like: utf-8''%E6%96%87.txt"""
    try:
        charset, _, encoded = value.partition("''")
        decoded = unquote(encoded)
        return decoded.encode("latin-1", "ignore").decode(charset or default_charset, "replace")
    except Exception:  # pragma: no cover
        return unquote(value)


def _decode_rfc5987(raw: bytes, charset: str) -> str:
    try:
        cs, _, enc = raw.partition(b"''")
        b = unquote_to_bytes(enc.decode("ascii", "ignore"))
        try:
            return b.decode(cs.decode() if isinstance(cs, bytes) else cs or charset, "replace")
        except Exception:
            return b.decode(charset or "utf-8", "replace")
    except Exception:
        return unquote(raw.decode("latin-1", "ignore"))
