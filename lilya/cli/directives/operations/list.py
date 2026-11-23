from warnings import warn

from .directives import directives as directives

warn("`list` is deprecated. Use `directives` instead.", DeprecationWarning, stacklevel=2)
