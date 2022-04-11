"""File connecting to the database session (allows to change it only while the session exists)"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal


async def get_db() -> AsyncSession:
    """Return database session"""

    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
