from lilya.exceptions import HTTPException
from lilya.status import HTTP_401_UNAUTHORIZED


class AuthenticationErrorMixin:
    def build_authentication_exception(
        self,
        headers: dict[str, str],
        detail: str = "Not authenticated",
        status_code: int = HTTP_401_UNAUTHORIZED,
    ) -> HTTPException:
        """
        When an API request is rejected due to missing or invalid credentials, the HTTP specification requires the
        server to return a 401 Unauthorized response that includes a WWW-Authenticate header.

        Although there is no official standard for using this header with API Key authentication,
        the requirement still applies. To meet this obligation, the system provides a custom authentication
        challenge using the APIKey scheme.

        This approach ensures clarity and consistency for anyone interacting with the API. Clients—whether
        automated systems or developers—receive a clear indication that an API Key is expected.
        Even without a formal standard, this behavior keeps error handling predictable and aligned with the
        HTTP specification.
        """
        return HTTPException(status_code=status_code, detail=detail, headers=headers)
