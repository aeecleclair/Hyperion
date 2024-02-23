from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core
from app.utils.types.groups_type import GroupType


async def disable_external_accounts(db: AsyncSession) -> bool:
    try:
        await db.execute(
            update(models_core.CoreUser)
            .where(models_core.CoreMembership.group_id == GroupType.external.value)
            .values(enabled=False)
        )
        return True
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
