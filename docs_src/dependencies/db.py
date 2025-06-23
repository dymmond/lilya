from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, sessionmaker
from lilya.apps import Lilya
from lilya.dependencies import Provide, Provides

# Setup engine & factory
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session

app = Lilya(
    dependencies={
        "db": Provide(get_db, use_cache=True)
    }
)

@app.get("/users/{user_id}")
async def read_user(user_id: int, db=Provides()):
    user = await db.get(User, user_id)
    return user.to_dict()
