from typing import Any

from lilya.exceptions import HTTPException
from lilya.responses import JSONResponse, Response


def abort(
    status_code: int,
    detail: Any | None = None,
    headers: dict[str, Any] | None = None,
) -> None:
    """
    Immediately raise an HTTPException that stops request processing.

    Examples:
        abort(404)
        abort(401, "Unauthorized")
        abort(400, {"error": "Bad Request"})
    """
    response: Response

    if isinstance(detail, (dict, list)):
        response = JSONResponse(detail, status_code=status_code, headers=headers)
        raise HTTPException(status_code=status_code, headers=headers, response=response)

    if detail is None:
        raise HTTPException(status_code=status_code, headers=headers)

    response = Response(detail, status_code=status_code, headers=headers)
    raise HTTPException(status_code=status_code, detail=detail, headers=headers, response=response)
