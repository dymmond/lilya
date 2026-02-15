from pydantic import BaseModel

from lilya.contrib.openapi.decorator import openapi
from lilya.enums import MediaType


class UploadBody(BaseModel):
    user: str
    file: bytes


@openapi(
    summary="Upload file",
    request_body=UploadBody,
    media_type=MediaType.MULTIPART,
)
async def upload_file(request): ...
