import os

os.environ.setdefault("OVERRIDE_SETTINGS_MODULE_VARIABLE", "LILYA_SETTINGS_MODULE")

if not os.environ.get("LILYA_SETTINGS_MODULE"):
    os.environ.setdefault("LILYA_SETTINGS_MODULE", "lilya.conf.global_settings.Settings")
from dymmond_settings import settings as settings  # noqa

from lilya.conf.global_settings import Settings as Settings  # noqa
