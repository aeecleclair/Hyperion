from app.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncSession:
    """Return database session"""

    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
