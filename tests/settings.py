import asyncio
import os
from functools import cached_property
from typing import Optional, Tuple

from lilya.conf.global_settings import Settings


class TestSettings(Settings):
    debug: bool = True
