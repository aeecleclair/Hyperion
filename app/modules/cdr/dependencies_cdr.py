from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.modules.cdr.coredata_cdr import CdrYear
from app.utils.tools import get_core_data


async def get_current_cdr_year(
    db: AsyncSession = Depends(get_db),
) -> CdrYear:
    """
    Dependency that returns the current cdr year
    """
    return await get_core_data(CdrYear, db)
