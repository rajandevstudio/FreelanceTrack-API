import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

# -----------------------------------------------------------------------------
# WHY A SEPARATE TEST DATABASE?
#
# We never run tests against your real database. Tests create and destroy data
# constantly — you'd corrupt real data and tests would interfere with each other.
#
# We use SQLite in async mode for tests — no PostgreSQL needed, no Docker needed,
# runs entirely in memory, gets wiped after every test session.
# -----------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables before tests, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Give each test a clean DB session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()  # undo any changes after each test


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    AsyncClient that uses the test DB instead of the real one.
    
    We override get_db with a version that returns our test session.
    This is FastAPI's dependency override system — very powerful for testing.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()