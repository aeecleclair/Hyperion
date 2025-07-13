"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ForeignKey, and_, delete, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_utils import get_referencing_foreign_keys

from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType
from app.core.schools.schools_type import SchoolType
from app.core.users import models_users, schemas_users


async def count_users(db: AsyncSession) -> int:
    """Return the number of users in the database"""

    result = await db.execute(select(models_users.CoreUser))
    return len(result.scalars().all())


async def get_users(
    db: AsyncSession,
    included_account_types: list[AccountType] | None = None,
    excluded_account_types: list[AccountType] | None = None,
    included_groups: list[str] | None = None,
    excluded_groups: list[str] | None = None,
    schools_ids: list[UUID] | None = None,
) -> Sequence[models_users.CoreUser]:
    """
    Return all users from database.

    Parameters `excluded_account_types` and `excluded_groups` can be used to filter results.
    """
    included_account_types = included_account_types or None
    excluded_account_types = excluded_account_types or []
    included_groups = included_groups or []
    excluded_groups = excluded_groups or []
    schools_ids = schools_ids or None

    # We want, for each group that should be included check if
    # - at least one of the user's groups match the expected group
    included_group_condition = [
        models_users.CoreUser.groups.any(
            models_groups.CoreGroup.id == group_id,
        )
        for group_id in included_groups
    ]
    included_account_type_condition = (
        or_(
            False,
            *[
                models_users.CoreUser.account_type == account_type
                for account_type in included_account_types
            ],
        )
        if included_account_types
        else and_(True)
    )
    # We want, for each group that should not be included
    # check that the following condition is false :
    # - at least one of the user's groups match the expected group
    excluded_group_condition = [
        not_(
            models_users.CoreUser.groups.any(
                models_groups.CoreGroup.id == group_id,
            ),
        )
        for group_id in excluded_groups
    ]
    excluded_account_type_condition = [
        not_(
            models_users.CoreUser.account_type == account_type,
        )
        for account_type in excluded_account_types
    ]
    school_condition = (
        or_(
            *[
                models_users.CoreUser.school_id == school_id
                for school_id in schools_ids
            ],
        )
        if schools_ids
        else and_(True)
    )

    result = await db.execute(
        select(models_users.CoreUser).where(
            and_(
                True,
                *included_group_condition,
                included_account_type_condition,
                *excluded_account_type_condition,
                *excluded_group_condition,
                school_condition,
            ),
        ),
    )
    return result.scalars().all()


async def get_user_by_id(
    db: AsyncSession,
    user_id: str,
) -> models_users.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_users.CoreUser)
        .where(models_users.CoreUser.id == user_id)
        .options(
            # The group relationship need to be loaded
            selectinload(models_users.CoreUser.groups),
        ),
    )
    return result.scalars().first()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> models_users.CoreUser | None:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_users.CoreUser)
        .where(models_users.CoreUser.email == email)
        .options(
            # The group relationship need to be loaded to be able
            # to check if the user is a member of a specific group
            selectinload(models_users.CoreUser.groups),
        ),
    )
    return result.scalars().first()


async def update_user(
    db: AsyncSession,
    user_id: str,
    user_update: schemas_users.CoreUserUpdateAdmin | schemas_users.CoreUserUpdate,
):
    await db.execute(
        update(models_users.CoreUser)
        .where(models_users.CoreUser.id == user_id)
        .values(**user_update.model_dump(exclude_none=True)),
    )


async def create_unconfirmed_user(
    db: AsyncSession,
    user_unconfirmed: models_users.CoreUserUnconfirmed,
) -> models_users.CoreUserUnconfirmed:
    """
    Create a new user in the unconfirmed database
    """

    db.add(user_unconfirmed)
    await db.flush()
    return user_unconfirmed  # TODO Is this useful ?


async def get_unconfirmed_user_by_activation_token(
    db: AsyncSession,
    activation_token: str,
) -> models_users.CoreUserUnconfirmed | None:
    result = await db.execute(
        select(models_users.CoreUserUnconfirmed).where(
            models_users.CoreUserUnconfirmed.activation_token == activation_token,
        ),
    )
    return result.scalars().first()


async def delete_unconfirmed_user_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_users.CoreUserUnconfirmed).where(
            models_users.CoreUserUnconfirmed.email == email,
        ),
    )
    await db.flush()


async def create_user(
    db: AsyncSession,
    user: models_users.CoreUser,
) -> models_users.CoreUser:
    db.add(user)
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_users.CoreUser).where(models_users.CoreUser.id == user_id),
    )
    await db.flush()


async def create_user_recover_request(
    db: AsyncSession,
    recover_request: models_users.CoreUserRecoverRequest,
) -> models_users.CoreUserRecoverRequest:
    db.add(recover_request)
    await db.flush()
    return recover_request


async def get_recover_request_by_reset_token(
    db: AsyncSession,
    reset_token: str,
) -> models_users.CoreUserRecoverRequest | None:
    result = await db.execute(
        select(models_users.CoreUserRecoverRequest).where(
            models_users.CoreUserRecoverRequest.reset_token == reset_token,
        ),
    )
    return result.scalars().first()


async def get_recover_request_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_users.CoreUserRecoverRequest | None:
    result = await db.execute(
        select(models_users.CoreUserRecoverRequest).where(
            models_users.CoreUserRecoverRequest.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def delete_recover_request_by_user_id(db: AsyncSession, user_id: str):
    await db.execute(
        delete(models_users.CoreUserRecoverRequest).where(
            models_users.CoreUserRecoverRequest.user_id == user_id,
        ),
    )
    await db.flush()


async def create_email_migration_request(
    migration_object: models_users.CoreUserEmailMigrationRequest,
    db: AsyncSession,
) -> models_users.CoreUserEmailMigrationRequest:
    db.add(migration_object)
    await db.flush()
    return migration_object


async def get_email_migration_request_by_token(
    confirmation_token: str,
    db: AsyncSession,
) -> models_users.CoreUserEmailMigrationRequest | None:
    result = await db.execute(
        select(models_users.CoreUserEmailMigrationRequest).where(
            models_users.CoreUserEmailMigrationRequest.confirmation_token
            == confirmation_token,
        ),
    )
    return result.scalars().first()


async def get_email_migration_request_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> models_users.CoreUserEmailMigrationRequest | None:
    result = await db.execute(
        select(models_users.CoreUserEmailMigrationRequest).where(
            models_users.CoreUserEmailMigrationRequest.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def delete_email_migration_request_by_token(
    confirmation_token: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_users.CoreUserEmailMigrationRequest).where(
            models_users.CoreUserEmailMigrationRequest.confirmation_token
            == confirmation_token,
        ),
    )
    await db.flush()


async def delete_email_migration_request_by_user_id(
    user_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_users.CoreUserEmailMigrationRequest).where(
            models_users.CoreUserEmailMigrationRequest.user_id == user_id,
        ),
    )
    await db.flush()


async def update_user_password_by_id(
    db: AsyncSession,
    user_id: str,
    new_password_hash: str,
):
    await db.execute(
        update(models_users.CoreUser)
        .where(models_users.CoreUser.id == user_id)
        .values(password_hash=new_password_hash),
    )
    await db.flush()


async def remove_users_from_school(
    db: AsyncSession,
    school_id: UUID,
):
    await db.execute(
        update(models_users.CoreUser)
        .where(
            models_users.CoreUser.school_id == school_id,
        )
        .values(
            school_id=SchoolType.no_school.value,
            account_type=AccountType.external,
        ),
    )


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
        models_users.CoreUser.__table__,
    )
    # We keep only the foreign keys that reference the user_id
    user_id_fks: list[ForeignKey] = [
        fk for fk in foreign_keys if fk.column == models_users.CoreUser.__table__.c.id
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
