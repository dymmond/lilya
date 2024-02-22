from contextlib import asynccontextmanager

from saffier import Database, Registry

from lilya.apps import Lilya
from lilya.requests import Request
from lilya.routing import Path

database = Database("postgresql+asyncpg://user:password@host:port/database")
registry = Registry(database=database)


async def create_user(request: Request) -> None:
    # Logic to create the user
    data = await request.json()
    ...


@asynccontextmanager
async def lifespan(app: Lilya):
    # What happens on startup
    await database.connect()
    yield
    # What happens on shutdown
    await database.disconnect()


app = Lilya(
    routes=[Path("/create", handler=create_user)],
    lifespan=lifespan,
)
