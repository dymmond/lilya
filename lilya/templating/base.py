from __future__ import annotations

import os
import sys
from typing import Any, Generic, TypeVar, Union

from lilya import status
from lilya.background import Task
from lilya.requests import Request
from lilya.responses import TemplateResponse

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

PathLike = Union[str, "os.PathLike[str]"]


class BaseTemplateRenderer(Generic[T]):
    def __init__(self, template: T) -> None:
        self.template = template

    def get_template(self, name: str) -> T:
        return self.template.get_template(name=name)  # type: ignore

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError()

    def prepare_response(
        self,
        request: Request,
        name: str,
        context: dict,
        status_code: int = status.HTTP_200_OK,
        headers: dict[str, Any] = None,
        media_type: str = None,
        background: Task | None = None,
    ) -> TemplateResponse:
        context.setdefault("request", request)
        template = self.get_template(name)
        return TemplateResponse(
            template=template,
            context=context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
