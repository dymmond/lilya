from lilya.apps import Lilya
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path

from .configs.app_settings import InstanceSettings


async def home(request: Request) -> JSONResponse: ...


app = Lilya(
    routes=[Path("/", handler=home)],
    settings_module=InstanceSettings,
)
