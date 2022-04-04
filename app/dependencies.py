# Dependency
from app.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncSession:
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
