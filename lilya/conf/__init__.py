import os

if not os.environ.get("SETTINGS_MODULE"):
    os.environ.setdefault("SETTINGS_MODULE", "lilya.conf.global_settings.Settings")
from dymmond_settings import settings as settings

from lilya.conf.global_settings import Settings as Settings
