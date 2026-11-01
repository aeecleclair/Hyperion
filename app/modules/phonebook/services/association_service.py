import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import models_users
from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.others import exceptions_phonebook
from app.modules.phonebook.others.shared import (
    association_if_exists,
    validate_rights,
    validate_rights_or_is_president,
)


async def get_all_associations(
    db: AsyncSession,
) -> Sequence[schemas_phonebook.AssociationComplete]:
    return await cruds_phonebook.get_all_associations(db)


async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession,
    user: models_users.CoreUser,
) -> schemas_phonebook.AssociationComplete:
    await validate_rights(
        db,
        user,
        association.groupement_id,
        f"You are not allowed to create an association for groupement {association.groupement_id}",
    )

    association_id = str(uuid.uuid4())
    association_model = schemas_phonebook.AssociationComplete(
        id=association_id,
        name=association.name,
        description=association.description,
        groupement_id=association.groupement_id,
        mandate_year=association.mandate_year,
        deactivated=association.deactivated,
    )

    await cruds_phonebook.create_association(association_model, db)

    await cruds_phonebook.update_association_groups(
        association_id=association_id,
        new_associated_group_ids=association.associated_groups,
        db=db,
    )

    return schemas_phonebook.AssociationComplete(
        id=association_id,
        **association.model_dump(),
    )


async def update_association(
    association_id: str,
    association_edit: schemas_phonebook.AssociationEdit,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> None:
    association = await association_if_exists(association_id, db)
    await validate_rights_or_is_president(
        association_id,
        association.mandate_year,
        association.groupement_id,
        user,
        db,
        f"You are not allowed to create an association for groupement {association.groupement_id}",
    )

    await cruds_phonebook.update_association(
        association_id=association_id,
        association_edit=association_edit,
        db=db,
    )


async def update_association_groups(
    association_id: str,
    association_groups_edit: schemas_phonebook.AssociationGroupsEdit,
    db: AsyncSession,
) -> None:
    await cruds_phonebook.update_association_groups(
        association_id=association_id,
        new_associated_group_ids=association_groups_edit.associated_groups,
        db=db,
    )


async def deactivate_association(
    association_id: str,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> None:
    association = await association_if_exists(association_id, db)
    await validate_rights(
        db,
        user,
        association.groupement_id,
        f"You are not allowed to deactivate association {association_id}",
    )

    await cruds_phonebook.deactivate_association(association_id, db)


async def delete_association(
    association_id: str,
    db: AsyncSession,
    user: models_users.CoreUser,
) -> None:
    association = await association_if_exists(association_id, db)
    await validate_rights(
        db,
        user,
        association.groupement_id,
        f"You are not allowed to delete association {association_id}",
    )
    if not association.deactivated:
        raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
            "Only deactivated associations can be deleted.",
        )

    await cruds_phonebook.delete_association(
        association_id=association_id,
        db=db,
    )


async def create_association_logo_validation(
    association_id: str,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> None:
    association = await association_if_exists(association_id, db)
    await validate_rights_or_is_president(
        association_id,
        association.mandate_year,
        association.groupement_id,
        user,
        db,
        f"You are not allowed to update association {association_id}",
    )


async def read_association_logo_validation(
    association_id: str,
    db: AsyncSession,
) -> None:
    await association_if_exists(association_id, db)
