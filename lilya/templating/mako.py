import os
from typing import List, Union

from lilya.exceptions import MissingDependency, TemplateNotFound

try:
    from mako.exceptions import TemplateLookupException as MakoTemplateNotFound
    from mako.lookup import TemplateLookup
    from mako.template import Template
except ImportError as exc:  # pragma: no cover
    raise MissingDependency("mako is not installed") from exc

PathLike = Union[str, "os.PathLike[str]"]


class MakoTemplate:
    def __init__(self, directory: Union[PathLike, List[PathLike]]) -> None:
        self.engine = TemplateLookup(
            directories=directory if isinstance(directory, (list, tuple)) else [directory]
        )

    def get_template(self, template_name: str) -> Template:  # pragma: no cover
        try:
            return self.engine.get_template(template_name)
        except MakoTemplateNotFound as e:
            raise TemplateNotFound(template_name=template_name) from e
