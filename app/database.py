"""File defining the asynchronous engine and database"""

from pydantic import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class DBSettings(BaseSettings):
    """Settings for the database, because app.core.config.Settings is not available in this file due to circular imports"""

    SQLITE_DB: bool = False  # If True, the application use a SQLite database instead of PostgreSQL, for testing or development purposes (should not be used if possible)
    ############################
    # PostgreSQL configuration #
    ############################
    # PostgreSQL configuration is needed to use the database
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    class Config:
        """Pydantic settings configuration"""

        env_file = ".env"


settings = DBSettings()

if settings.SQLITE_DB:
    SQLALCHEMY_DATABASE_URL = (
        "sqlite+aiosqlite:///./sql_app.db"  # Connect to the test's database
    )
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}"

# Echo write the SQL queries in terminal, should be disabled in prod
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)


Base = declarative_base()

SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
