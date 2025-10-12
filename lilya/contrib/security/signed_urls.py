from __future__ import annotations

import base64
import hmac
import time
from typing import Any
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse

from lilya.responses import RedirectResponse


class SignedURLGenerator:
    """
    Generates and verifies time-limited, signed URLs using the HMAC-SHA256 algorithm.

    This class provides a mechanism to ensure that URLs distributed to clients are
    **tamper-proof** and are only valid within a specified **expiration window**.
    The signature (`sig`) covers the URL path and all query parameters, including
    the mandatory expiration timestamp (`expires`), offering strong integrity checks.

    Example usage:
        >>> signer = SignedURLGenerator(secret_key="supersecret")
        >>> signed = signer.sign("https://example.com/download", expires_in=300)
        >>> print(signed)
        'https://example.com/download?expires=...&sig=...'
        >>> signer.verify(signed)
        True
    """

    def __init__(self, secret_key: str, algorithm: str = "sha256") -> None:
        """
        Initializes the URL generator with a secret key and a hashing algorithm.

        Args:
            secret_key: The cryptographic key used to generate the HMAC signature.
                        This key **must be kept secret** and must be identical on
                        both the signing and verification sides for security.
            algorithm: The hashing algorithm name recognized by the `hashlib` module
                       (e.g., 'sha256', 'sha512'). Defaults to 'sha256'.
        """
        self.secret_key: bytes = secret_key.encode()
        self.algorithm: str = algorithm

    def sign(self, url: str, expires_in: int = 3600) -> str:
        """
        Attaches an HMAC signature and an expiration timestamp to a given URL.

        The method performs the following steps:
        1. Adds the `expires` timestamp (current time + `expires_in`) to the query parameters.
        2. Generates an HMAC signature over the URL's path and the full query string (including `expires`).
        3. Appends the signature as the `sig` query parameter.

        Args:
            url: The base URL to be signed (e.g., 'https://example.com/resource').
            expires_in: The duration in seconds for which the generated URL will be valid.
                        Defaults to 3600 seconds (1 hour).

        Returns:
            The final signed URL string containing the `expires` and `sig` query parameters.
        """
        # Parse the input URL into its components
        parsed: ParseResult = urlparse(url)
        # Parse existing query parameters into a mutable dictionary for modification
        params: dict[str, str] = dict(parse_qsl(parsed.query))

        # Calculate expiration timestamp (Unix time) and add to parameters
        expires: int = int(time.time()) + expires_in
        params["expires"] = str(expires)

        # Re-encode parameters for signing: must be done *before* adding the signature
        query: str = urlencode(params)
        # The data to be signed is the path and the canonicalized query string
        to_sign: bytes = f"{parsed.path}?{query}".encode()

        # Generate HMAC signature
        signature: bytes = hmac.new(self.secret_key, to_sign, self.algorithm).digest()

        # Encode signature using URL-safe base64 and remove padding ('=') for cleaner URLs
        sig_b64: str = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        # Construct the final signed query string by adding the signature
        signed_query: str = f"{query}&sig={sig_b64}"

        # Rebuild and return the full URL
        return urlunparse(parsed._replace(query=signed_query))

    def verify(self, signed_url: str) -> bool:
        """
        Verifies the validity and integrity of a signed URL.

        The verification process ensures:
        1. **Existence:** The `sig` and `expires` parameters must be present.
        2. **Time Check:** The current time must be less than the `expires` timestamp.
        3. **Integrity Check:** The calculated HMAC signature (derived from the URL path and parameters, excluding the passed `sig`) must exactly match the provided `sig`.

        Args:
            signed_url: The full URL string containing the `expires` and `sig` parameters.

        Returns:
            True if the URL is valid, unexpired, and the signature matches; False otherwise.
        """
        # Parse the signed URL
        parsed: ParseResult = urlparse(signed_url)

        # Extract query parameters
        params: dict[str, str] = dict(parse_qsl(parsed.query))

        # Extract and perform initial validation
        sig: str | None = params.pop("sig", None)
        expires_str: str = params.get("expires", "0")

        # Signature must exist
        if not sig:
            return False

        # Validate expiration time format and check for expiry
        try:
            expires: int = int(expires_str)
        except ValueError:
            # Return False if the 'expires' parameter is malformed
            return False

        if time.time() > expires:
            return False

        # Signature Integrity Check
        # Re-encode parameters *without* the signature to calculate the expected HMAC
        query: str = urlencode(params)
        to_sign: bytes = f"{parsed.path}?{query}".encode()

        # Calculate the expected signature
        expected_sig: bytes = hmac.new(self.secret_key, to_sign, self.algorithm).digest()
        expected_sig_b64: str = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        # Use hmac.compare_digest for constant-time comparison. This is critical to prevent **timing attacks**.
        return hmac.compare_digest(expected_sig_b64, sig)


class SignedRedirect(RedirectResponse):
    """
    A redirect response that automatically signs its target URL using `SignedURLGenerator`.

    This ensures the redirected URL is **tamper-proof** and **time-limited**.

    Example:
        >>> signer = SignedURLGenerator("my-secret")
        >>> response = SignedRedirect("https://example.com/secure", signer, expires_in=120)
        >>> response.status_code
        307
        >>> response.headers["Location"]
        'https://example.com/secure?expires=...&sig=...'

    Args:
        url: The target URL to redirect to.
        signer: Instance of `SignedURLGenerator` used to sign the target URL.
        expires_in: Expiration time in seconds for the signed URL. Defaults to 3600 (1 hour).
        status_code: HTTP status code for the redirect. Defaults to 307.
    """

    def __init__(
        self,
        url: str,
        signer: SignedURLGenerator,
        *,
        expires_in: int = 3600,
        status_code: int = 307,
        **kwargs: Any,
    ) -> None:
        signed_url = signer.sign(url, expires_in=expires_in)
        super().__init__(url=signed_url, status_code=status_code, **kwargs)
