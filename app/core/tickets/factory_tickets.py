from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.config import Settings
from app.types.factory import Factory


class TicketsFactory(Factory):
    depends_on = []

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        pass

    @classmethod
    async def should_run(cls, db: AsyncSession):
        pass
