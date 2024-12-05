"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence

from sqlalchemy import ForeignKey, and_, delete, not_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_utils import get_referencing_foreign_keys  # type: ignore

from app.core import models_core, schemas_core
from app.core.groups.groups_type import AccountType


async def count_users(db: AsyncSession) -> int:
    """Return the number of users in the database"""

    result = await db.execute(select(models_core.CoreUser))
    return len(result.scalars().all())


async def get_users(
    db: AsyncSession,
    included_account_types: list[AccountType] | None = None,
    excluded_account_types: list[AccountType] | None = None,
    included_groups: list[str] | None = None,
    excluded_groups: list[str] | None = None,
) -> Sequence[models_core.CoreUser]:
    """
    Return all users from database.

    Parameters `excluded_account_types` and `excluded_groups` can be used to filter results.
    """
    included_account_types = included_account_types or list(AccountType)
    excluded_account_types = excluded_account_types or []
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
                or_(
                    False,
                    *[
                        models_core.CoreUser.account_type == account_type
                        for account_type in included_account_types
                    ],
                ),
                *[
                    not_(
                        models_core.CoreUser.account_type == account_type,
                    )
                    for account_type in excluded_account_types
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
    """Fusion two users together
    We use the user_kept_id as the user that will keep all the data
    and the user_deleted_id as the user that will be deleted

    The function will update all the foreign keys that reference the user_deleted_id
    to reference the user_kept_id instead

    If the user_deleted_id is referenced in a table where the user_kept_id is also referenced,
    and the change would create a duplicate that violates a unique constraint, the row will be deleted

    There are three cases to consider:
    1. The foreign key is not a primary key of the table:
        In this case, we can update the row
    2. The foreign key is one of the primary keys of the table:
        In this case, we can't update the row without verifying that the new row doesn't already exist
        So we collect all the primary keys of the table where the user_deleted_id is referenced and
        all the primary keys of the table where the user_kept_id is referenced
        We then update the row and check if the new row already exists:
            a. If it doesn't, we update the row
            b. If it does, we delete the row
    """
    foreign_keys: set[ForeignKey] = get_referencing_foreign_keys(
        models_core.CoreUser.__table__,
    )
    # We keep only the foreign keys that reference the user_id
    user_id_fks: list[ForeignKey] = [
        fk for fk in foreign_keys if fk.column == models_core.CoreUser.__table__.c.id
    ]
    for fk in user_id_fks:
        is_in = False
        # We can not use `if fk.parent in fk.parent.table.primary_key.columns` because `in` doesn't work with columns
        for pk in fk.parent.table.primary_key.columns:
            if fk.parent == pk:
                is_in = True
                break
        if not is_in:  # Case 1
            await db.execute(
                update(fk.parent.table)
                .where(fk.parent == user_deleted_id)
                .values(**{fk.parent.name: user_kept_id}),
            )
        else:  # Case 2
            primary_key_columns = list(fk.parent.table.primary_key.columns)

            kept_user_data = (  # We get all the data where the user_kept_id is referenced
                await db.execute(
                    select(fk.parent.table).where(fk.parent == user_kept_id),
                )
            ).all()
            kept_user_primaries_data = [  # We keep only the primary keys
                [getattr(data, col.name) for col in primary_key_columns]
                for data in kept_user_data
            ]

            deleted_user_data = (  # We get all the data where the user_deleted_id is referenced
                await db.execute(
                    select(fk.parent.table).where(
                        fk.parent == user_deleted_id,
                    ),
                )
            ).all()
            deleted_user_primaries_data = [  # We keep only the primary keys
                [getattr(data, col.name) for col in primary_key_columns]
                for data in deleted_user_data
            ]

            for i in range(len(deleted_user_primaries_data)):
                user_id_fk_index = deleted_user_primaries_data[i].index(user_deleted_id)
                deleted_user_primaries_data[i][user_id_fk_index] = (
                    user_kept_id  # We replace the user_deleted_id by the user_kept_id in the deleted_user_primaries_data
                )
                if (
                    deleted_user_primaries_data[i] not in kept_user_primaries_data
                ):  # Case 2a
                    deleted_user_primaries_data[i][user_id_fk_index] = (
                        user_deleted_id  # We put back the user_deleted_id in the deleted_user_primaries_data to update the row
                    )
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
                        .values(**{fk.parent.name: user_kept_id}),
                    )
                else:  # Case 2b
                    deleted_user_primaries_data[i][user_id_fk_index] = (
                        user_deleted_id  # We put back the user_deleted_id in the deleted_user_primaries_data to delete the row
                    )
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

    # Delete the user_deleted
    await delete_user(db, user_deleted_id)
