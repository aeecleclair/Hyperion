from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core
from app.utils.types.groups_type import GroupType


async def disable_external_accounts(db: AsyncSession):
    try:
        await db.execute(
            update(models_core.CoreUser)
            .where(
                models_core.CoreUser.groups.any(
                    models_core.CoreGroup.id == GroupType.external.value
                )
            )
            .values(disabled=True)
        )
        await db.commit()

    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
