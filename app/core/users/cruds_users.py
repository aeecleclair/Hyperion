"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence

from sqlalchemy import ForeignKey, and_, delete, not_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_utils import get_referencing_foreign_keys  # type: ignore

from app.core import models_core, schemas_core


async def count_users(db: AsyncSession) -> int:
    """Return the number of users in the database"""

    result = await db.execute(select(models_core.CoreUser))
    return len(result.scalars().all())


async def get_users(
    db: AsyncSession,
    included_groups: list[str] | None = None,
    excluded_groups: list[str] | None = None,
) -> Sequence[models_core.CoreUser]:
    """
    Return all users from database.

    Parameters `included_groups` and `excluded_groups` can be used to filter results.
    """
    included_groups = included_groups or []
    excluded_groups = excluded_groups or []

    result = await db.execute(
        select(models_core.CoreUser).where(
            and_(
                True,
                # We want, for each group that should be included check if
                # - at least one of the user's groups match the expected group
                *[
                    models_core.CoreUser.groups.any(
                        models_core.CoreGroup.id == group_id,
                    )
                    for group_id in included_groups
                ],
                # We want, for each group that should not be included
                # check that the following condition is false :
                # - at least one of the user's groups match the expected group
                *[
                    not_(
                        models_core.CoreUser.groups.any(
                            models_core.CoreGroup.id == group_id,
                        ),
                    )
                    for group_id in excluded_groups
                ],
            ),
        ),
    )
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: str) -> models_core.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .options(
            # The group relationship need to be loaded
            selectinload(models_core.CoreUser.groups),
        ),
    )
    return result.scalars().first()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> models_core.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.email == email)
        .options(
            # The group relationship need to be loaded to be able
            # to check if the user is a member of a specific group
            selectinload(models_core.CoreUser.groups),
        ),
    )
    return result.scalars().first()


async def update_user(
    db: AsyncSession,
    user_id: str,
    user_update: schemas_core.CoreUserUpdateAdmin | schemas_core.CoreUserUpdate,
):
    await db.execute(
        update(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .values(**user_update.model_dump(exclude_none=True)),
    )
    await db.commit()


async def create_unconfirmed_user(
    db: AsyncSession,
    user_unconfirmed: models_core.CoreUserUnconfirmed,
) -> models_core.CoreUserUnconfirmed:
    """
    Create a new user in the unconfirmed database
    """

    db.add(user_unconfirmed)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return user_unconfirmed  # TODO Is this useful ?


async def get_unconfirmed_user_by_activation_token(
    db: AsyncSession,
    activation_token: str,
) -> models_core.CoreUserUnconfirmed | None:
    result = await db.execute(
        select(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.activation_token == activation_token,
        ),
    )
    return result.scalars().first()


async def delete_unconfirmed_user_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.email == email,
        ),
    )
    await db.commit()


async def create_user(
    db: AsyncSession,
    user: models_core.CoreUser,
) -> models_core.CoreUser:
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return user


async def delete_user(db: AsyncSession, user_id: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id),
    )
    await db.commit()


async def create_user_recover_request(
    db: AsyncSession,
    recover_request: models_core.CoreUserRecoverRequest,
) -> models_core.CoreUserRecoverRequest:
    db.add(recover_request)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return recover_request


async def get_recover_request_by_reset_token(
    db: AsyncSession,
    reset_token: str,
) -> models_core.CoreUserRecoverRequest | None:
    result = await db.execute(
        select(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.reset_token == reset_token,
        ),
    )
    return result.scalars().first()


async def create_email_migration_code(
    migration_object: models_core.CoreUserEmailMigrationCode,
    db: AsyncSession,
) -> models_core.CoreUserEmailMigrationCode:
    db.add(migration_object)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return migration_object


async def get_email_migration_code_by_token(
    confirmation_token: str,
    db: AsyncSession,
) -> models_core.CoreUserEmailMigrationCode | None:
    result = await db.execute(
        select(models_core.CoreUserEmailMigrationCode).where(
            models_core.CoreUserEmailMigrationCode.confirmation_token
            == confirmation_token,
        ),
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
        ),
    )
    await db.commit()


async def update_user_email_by_id(
    user_id: str,
    new_email: str,
    db: AsyncSession,
    make_user_external: bool = False,
):
    try:
        await db.execute(
            update(models_core.CoreUser)
            .where(models_core.CoreUser.id == user_id)
            .values(email=new_email, external=make_user_external),
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_recover_request_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserRecoverRequest).where(
            models_core.CoreUserRecoverRequest.email == email,
        ),
    )
    await db.commit()


async def update_user_password_by_id(
    db: AsyncSession,
    user_id: str,
    new_password_hash: str,
):
    await db.execute(
        update(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .values(password_hash=new_password_hash),
    )
    await db.commit()


async def fusion_users(
    db: AsyncSession,
    user_kept_id: str,
    user_deleted_id: str,
):
    """Fusion two users together"""
    foreign_keys: set[ForeignKey] = get_referencing_foreign_keys(
        models_core.CoreUser.__table__,
    )
    user_id_fks = [
        fk for fk in foreign_keys if fk.column == models_core.CoreUser.__table__.c.id
    ]
    # Update the user_id of the user_deleted in the table core_association_membership
    for fk in user_id_fks:
        if fk.parent not in fk.parent.table.primary_key.columns:
            await db.execute(
                update(fk.parent.table)
                .where(fk.parent.column == user_deleted_id)
                .values(**{fk.column.name: user_kept_id}),
            )
        else:
            primary_key_columns = list(fk.parent.table.primary_key.columns)
            user_id_fk_index = primary_key_columns.index(fk.parent.column)
            kept_user_data = (
                (
                    await db.execute(
                        select(fk.parent.table).where(fk.parent.column == user_kept_id),
                    )
                )
                .scalars()
                .all()
            )
            kept_user_primaries_data = [
                getattr(data, col.name)
                for col in primary_key_columns
                for data in kept_user_data
            ]
            deleted_user_data = (
                (
                    await db.execute(
                        select(fk.parent.table).where(
                            fk.parent.column == user_deleted_id,
                        ),
                    )
                )
                .scalars()
                .all()
            )
            deleted_user_primaries_data = [
                getattr(data, col.name)
                for col in primary_key_columns
                for data in deleted_user_data
            ]
            for i in range(len(deleted_user_primaries_data)):
                deleted_user_primaries_data[i][user_id_fk_index] = (
                    kept_user_primaries_data[i]
                )
            for i in range(len(deleted_user_primaries_data)):
                if deleted_user_primaries_data[i] not in kept_user_primaries_data:
                    deleted_user_primaries_data[i][user_id_fk_index] = user_deleted_id
                    await db.execute(
                        update(fk.parent.table)
                        .where(
                            and_(
                                *[
                                    col == val
                                    for col, val in zip(
                                        primary_key_columns,
                                        deleted_user_primaries_data[i],
                                        strict=True,
                                    )
                                ],
                            ),
                        )
                        .values(**{fk.column.name: user_kept_id}),
                    )
                else:
                    deleted_user_primaries_data[i][user_id_fk_index] = user_deleted_id
                    await db.execute(
                        delete(fk.parent.table).where(
                            and_(
                                *[
                                    col == val
                                    for col, val in zip(
                                        primary_key_columns,
                                        deleted_user_primaries_data[i],
                                        strict=True,
                                    )
                                ],
                            ),
                        ),
                    )

    await db.execute(
        update(models_core.CoreAssociationMembership)
        .where(models_core.CoreAssociationMembership.user_id == user_deleted_id)
        .values(user_id=user_kept_id),
    )

    # Delete the user_deleted
    await delete_user(db, user_deleted_id)
