from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_notification


async def create_message(
    message: models_notification.Message,
    db: AsyncSession,
) -> None:
    """Create a new raffle in database and return it"""

    db.add(message)
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_firebase_devices_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> list[models_notification.FirebaseDevice]:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.user_id == user_id
        )
    )
    return result.scalars().all()
