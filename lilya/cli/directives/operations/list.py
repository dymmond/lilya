from warnings import warn

from .directives import directives as directives

warn("Use `directives` instead", DeprecationWarning, stacklevel=1)
