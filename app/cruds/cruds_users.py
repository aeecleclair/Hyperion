"""File defining the functions called by the endpoints, making queries to the table using the models"""

from typing import Sequence

from sqlalchemy import and_, delete, not_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_core

# from app.schemas.schemas_core import CoreUserUpdate


async def count_users(db: AsyncSession) -> int:
    """Return the number of users in the database"""

    result = await db.execute(select(models_core.CoreUser))
    return len(result.scalars().all())


async def get_users(
    db: AsyncSession,
    includedGroups: list[str] = [],
    excludedGroups: list[str] = [],
) -> Sequence[models_core.CoreUser]:
    """
    Return all users from database.

    Parameters `includedGroups` and `excludedGroups` can be used to filter results.
    """

    result = await db.execute(
        select(models_core.CoreUser).where(
            and_(
                True,
                # We want, for each group that should be included check if
                # - at least one of the user's groups match the expected group
                *[
                    models_core.CoreUser.groups.any(
                        models_core.CoreGroup.id == group_id
                    )
                    for group_id in includedGroups
                ],
                # We want, for each group that should not be included
                # check that the following condition is false :
                # - at least one of the user's groups match the expected group
                *[
                    not_(
                        models_core.CoreUser.groups.any(
                            models_core.CoreGroup.id == group_id
                        )
                    )
                    for group_id in excludedGroups
                ],
            )
        )
    )
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: str) -> models_core.CoreUser | None:
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


async def update_user(db: AsyncSession, user_id: str, user_update):
    await db.execute(
        update(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .values(**user_update.dict(exclude_none=True))
    )
    await db.commit()


async def create_unconfirmed_user(
    db: AsyncSession, user_unconfirmed: models_core.CoreUserUnconfirmed
) -> models_core.CoreUserUnconfirmed:
    """
    Create a new user in the unconfirmed database
    """

    db.add(user_unconfirmed)
    try:
        await db.commit()
        return user_unconfirmed  # TODO Is this useful ?
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_unconfirmed_user_by_activation_token(
    db: AsyncSession, activation_token: str
) -> models_core.CoreUserUnconfirmed | None:
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
    db: AsyncSession, user: models_core.CoreUser
) -> models_core.CoreUser:
    db.add(user)
    try:
        await db.commit()
        return user
    except IntegrityError:
        await db.rollback()
        raise


async def delete_user(db: AsyncSession, user_id: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    await db.commit()


async def create_user_recover_request(
    db: AsyncSession, recover_request: models_core.CoreUserRecoverRequest
) -> models_core.CoreUserRecoverRequest:
    db.add(recover_request)
    try:
        await db.commit()
        return recover_request
    except IntegrityError:
        await db.rollback()
        raise


async def get_recover_request_by_reset_token(
    db: AsyncSession, reset_token: str
) -> models_core.CoreUserRecoverRequest | None:
    result = await db.execute(
        select(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.reset_token == reset_token
        )
    )
    return result.scalars().first()


async def create_email_migration_code(
    migration_object: models_core.CoreUserEmailMigrationCode,
    db: AsyncSession,
) -> models_core.CoreUserEmailMigrationCode:
    db.add(migration_object)
    try:
        await db.commit()
        return migration_object
    except IntegrityError:
        await db.rollback()
        raise


async def get_email_migration_code_by_token(
    confirmation_token: str,
    db: AsyncSession,
) -> models_core.CoreUserEmailMigrationCode | None:
    result = await db.execute(
        select(models_core.CoreUserEmailMigrationCode).where(
            models_core.CoreUserEmailMigrationCode.confirmation_token
            == confirmation_token,
        )
    )
    return result.scalars().first()


async def delete_email_migration_code_by_token(
    confirmation_token: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.CoreUserEmailMigrationCode).where(
            models_core.CoreUserEmailMigrationCode.confirmation_token
            == confirmation_token,
        )
    )
    await db.commit()


async def update_user_email_by_id(
    user_id: str,
    new_email: str,
    db: AsyncSession,
):
    try:
        await db.execute(
            update(models_core.CoreUser)
            .where(models_core.CoreUser.id == user_id)
            .values(email=new_email)
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_recover_request_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.email == email
        )
    )
    await db.commit()


async def update_user_password_by_id(
    db: AsyncSession, user_id: str, new_password_hash: str
):
    await db.execute(
        update(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .values(password_hash=new_password_hash)
    )
    await db.commit()
