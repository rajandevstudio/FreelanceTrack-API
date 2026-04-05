from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# -----------------------------------------------------------------------------
# WHY ASYNC?
# In a regular (sync) Django/Flask app, when your code hits the DB, Python
# literally WAITS — the thread is blocked doing nothing.
# With async, while waiting for DB, Python can handle OTHER requests.
# For an API with many concurrent users, this is a huge performance win.
# -----------------------------------------------------------------------------

# create_async_engine uses asyncpg under the hood (not psycopg2)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",  # logs all SQL in dev — very helpful!
    pool_size=10,         # max 10 persistent DB connections
    max_overflow=20,      # up to 20 extra connections under heavy load
)

# async_sessionmaker is the factory that creates DB sessions
# expire_on_commit=False means objects stay usable after commit (important in async)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# All models will inherit from this Base.
# SQLAlchemy uses it to know which classes are DB tables.
class Base(DeclarativeBase):
    pass


# -----------------------------------------------------------------------------
# get_db is a FastAPI dependency — we'll use it like this in routers:
#
#   async def my_route(db: AsyncSession = Depends(get_db)):
#       result = await db.execute(...)
#
# The `yield` makes it a context manager:
#   - Opens session before your route runs
#   - Closes (and rolls back on error) after it finishes
# This ensures no session leaks, even if an exception is raised.
# -----------------------------------------------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise