from __future__ import annotations

import os
from typing import Any, Generic, TypeVar

from lilya import status
from lilya.background import Task
from lilya.requests import Request
from lilya.responses import TemplateResponse

T = TypeVar("T")

PathLike = str | os.PathLike[str]


class BaseTemplateRenderer(Generic[T]):
    def __init__(self, template: T, render_function_name: str = "render") -> None:
        self.template = template
        self.render_function_name = render_function_name

    def get_template(self, name: str) -> T:
        return self.template.get_template(name=name)  # type: ignore

    def __call__(self, *args: Any, **kwargs: Any) -> T:
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
            render_function_name=self.render_function_name,
        )
