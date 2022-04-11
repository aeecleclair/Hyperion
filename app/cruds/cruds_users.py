"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import models_core
from app.schemas import schemas_core


async def get_users(db: AsyncSession) -> list[models_core.CoreUser]:
    """Return all users from database"""

    result = await db.execute(select(models_core.CoreUser))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int) -> models_core.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .options(
            # The group relationship need to be loaded
            selectinload(models_core.CoreUser.groups)
        )
    )
    return result.scalars().first()


async def get_user_by_email(
    db: AsyncSession, email: str
) -> models_core.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser).where(models_core.CoreUser.email == email)
    )
    return result.scalars().first()


async def create_unconfirmed_user(
    db: AsyncSession, user_unconfirmed: schemas_core.CoreUserUnconfirmedInDB
) -> models_core.CoreUserUnconfirmed:
    """
    Create a new user in the unconfirmed database
    """

    db_user_unconfirmed = models_core.CoreUserUnconfirmed(**user_unconfirmed.dict())

    db.add(db_user_unconfirmed)
    try:
        await db.commit()
        return db_user_unconfirmed
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_unconfirmed_user_by_activation_token(
    db: AsyncSession, activation_token: str
) -> models_core.CoreUserUnconfirmed:

    result = await db.execute(
        select(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.activation_token == activation_token
        )
    )
    return result.scalars().first()


async def delete_unconfirmed_user_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.email == email
        )
    )
    await db.commit()


async def create_user(
    db: AsyncSession, user: schemas_core.CoreUserInDB
) -> models_core.CoreUser:

    db_user = models_core.CoreUser(**user.dict())

    db.add(db_user)
    try:
        await db.commit()
        return db_user
    except:
        await db.rollback()
        raise


async def delete_user(db: AsyncSession, user_id: int):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    await db.commit()


async def create_user_recover_request(
    db: AsyncSession, recover_request: schemas_core.CoreUserRecoverRequest
) -> models_core.CoreUserRecoverRequest:

    db_user = models_core.CoreUserRecoverRequest(**recover_request.dict())

    db.add(db_user)
    try:
        await db.commit()
        return db_user
    except:
        await db.rollback()
        raise


async def get_recover_request_by_reset_token(
    db: AsyncSession, reset_token: str
) -> models_core.CoreUserRecoverRequest:

    result = await db.execute(
        select(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.reset_token == reset_token
        )
    )
    return result.scalars().first()


async def delete_recover_request_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.email == email
        )
    )
    await db.commit()


async def update_user_password_by_id(db: AsyncSession, id: str, new_password_hash: str):
    pass
