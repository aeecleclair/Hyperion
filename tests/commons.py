from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = (
    "sqlite+aiosqlite:///./test.db"  # Connect to the test's database
)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)  # Create a session for testing purposes


@app.on_event("startup")
async def startuptest():
    # create db tables in test.db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def override_get_db() -> AsyncSession:
    """Override the get_db function to use the testing session"""

    async with TestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


app.dependency_overrides[get_db] = override_get_db


def test_create_db():  # A first test is needed to run startuptest once
    with TestClient(app):
        pass


client = TestClient(app)  # Create a client to execute tests
