from __future__ import annotations

from collections.abc import Mapping

from lilya import status


class HeaderHelper:
    # According to https://tools.ietf.org/html/rfc2616#section-7.1
    entity_headers: list[str] = [
        "allow",
        "content-encoding",
        "content-language",
        "content-length",
        "content-location",
        "content-md5",
        "content-range",
        "content-type",
        "expires",
        "last-modified",
        "extension-header",
    ]

    @classmethod
    def is_entity_header(cls, header: str) -> bool:
        return bool(header.lower() in cls.entity_headers)

    @classmethod
    def has_entity_header_status(cls, status_code: int) -> bool:
        return bool(
            status_code in (status.HTTP_304_NOT_MODIFIED, status.HTTP_412_PRECONDITION_FAILED)
        )

    @classmethod
    def remove_entity_headers(
        cls, headers: Mapping[str, str], allowed: tuple[str, str] | None = None
    ) -> dict[str, str]:
        """
        Removes all the entity headers present in the headers given.
        According to RFC 2616 Section 10.3.5.

        https://tools.ietf.org/html/rfc2616#section-10.3.5
        """
        if allowed is None:
            allowed = ("content-location", "expires")

        _allowed: set[str] = {h.lower() for h in allowed}
        headers = {
            header: value
            for header, value in headers.items()
            if not cls.is_entity_header(header) or header.lower() in _allowed
        }
        return headers

    @classmethod
    def has_body_message(cls, status_code: int) -> bool:
        """
        Based on the RFC specificiation the response status of 1XX, 204 and 304
        body and length **MUST NOT** be included.

        https://tools.ietf.org/html/rfc2616#section-4.4
        https://tools.ietf.org/html/rfc2616#section-4.3
        """
        return bool(status_code not in (204, 304) and not (100 <= status_code < 200))

    @classmethod
    def get_content_type(self, charset: str, media_type: str | None = None) -> str:
        """
        Builds the content-type based on the media type and charset.
        """
        if media_type is not None and media_type.startswith("text/"):
            return f"{media_type}; charset={charset}"
        return media_type
