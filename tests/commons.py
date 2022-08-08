from functools import lru_cache
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.database import Base
from app.dependencies import get_db, get_settings
from app.main import app
from app.models import models_core
from app.utils.types.groups_type import AccountType

SQLALCHEMY_DATABASE_URL = (
    "sqlite+aiosqlite:///./test.db"  # Connect to the test's database
)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)  # Create a session for testing purposes


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db function to use the testing session"""

    async with TestingSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@lru_cache()
def override_get_settings() -> Settings:
    """Override the get_settings function to use the testing session"""
    return Settings(_env_file=".env.test")


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_settings] = override_get_settings


@app.on_event("startup")
async def commonstartuptest():
    # create db tables in test.db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Add the necessary groups for account types
    description = "Account type"
    account_types = [
        models_core.CoreGroup(id=id, name=id.name, description=description)
        for id in AccountType
    ]
    async with TestingSessionLocal() as db:
        db.add_all(account_types)
        await db.commit()


client = TestClient(app)  # Create a client to execute tests
