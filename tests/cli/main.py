import os

import pytest

from lilya.apps import Lilya
from lilya.conf import settings

database, models = settings.registry

pytestmark = pytest.mark.anyio

basedir = os.path.abspath(os.path.dirname(__file__))

app = Lilya(routes=[], on_startup=[database.connect], on_shutdown=[database.disconnect])
