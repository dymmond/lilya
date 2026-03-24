from __future__ import annotations

import warnings

from lilya.compat import import_string as import_string

warnings.warn(
    "This module is deprecated. Use either `monkay.load` directly or `lilya.compat.import_string`.",
    DeprecationWarning,
    1,
)
