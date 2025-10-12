from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides
from lilya.enums import Scope
from myapp.db import connect_to_db

app = Lilya(
    dependencies={
        "db": Provide(connect_to_db, scope=Scope.REQUEST, use_cache=True)
    }
)

@app.get("/users")
async def list_users(db=Provides()):
    return await db.fetch_all("SELECT * FROM users")
