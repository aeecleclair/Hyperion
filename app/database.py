"""File defining the asynchronous engine and database"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://user:password@hyperion-db/db"

# Echo write the SQL queries in terminal, should be disabled in prod
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)


Base = declarative_base()

SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
