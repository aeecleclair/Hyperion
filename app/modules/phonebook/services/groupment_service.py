import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.others import exceptions_phonebook


async def get_all_groupements(
    db: AsyncSession,
) -> Sequence[schemas_phonebook.AssociationGroupement]:
    return await cruds_phonebook.get_all_groupements(db)


async def create_groupement(
    groupement_base: schemas_phonebook.AssociationGroupementBase,
    db: AsyncSession,
) -> schemas_phonebook.AssociationGroupement:
    groupement_db = await cruds_phonebook.get_groupement_by_name(
        groupement_name=groupement_base.name,
        db=db,
    )
    if groupement_db is not None:
        raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
            f"Groupement with name {groupement_base.name} already exists.",
        )

    groupement = schemas_phonebook.AssociationGroupement(
        id=uuid.uuid4(),
        name=groupement_base.name,
        manager_group_id=groupement_base.manager_group_id,
    )
    await cruds_phonebook.create_groupement(
        groupement=groupement,
        db=db,
    )
    return groupement


async def update_groupement(
    groupement_id: uuid.UUID,
    groupement_edit: schemas_phonebook.AssociationGroupementBase,
    db: AsyncSession,
):
    groupement = await cruds_phonebook.get_groupement_by_id(
        groupement_id=groupement_id,
        db=db,
    )
    if groupement is None:
        raise exceptions_phonebook.NotFoundException(  # noqa: TRY003
            "Groupement not found.",
        )
    if groupement.name != groupement_edit.name:
        existing_groupement = await cruds_phonebook.get_groupement_by_name(
            groupement_name=groupement_edit.name,
            db=db,
        )
        if existing_groupement is not None:
            raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
                f"Groupement with name {groupement_edit.name} already exists.",
            )

    await cruds_phonebook.update_groupement(
        groupement_id=groupement_id,
        groupement_edit=groupement_edit,
        db=db,
    )


async def delete_groupement(
    groupement_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    associations = await cruds_phonebook.get_associations_by_groupement_id(
        groupement_id=groupement_id,
        db=db,
    )
    if associations:
        raise exceptions_phonebook.BadRequestException(
            detail="You cannot delete a groupement that has associations linked to it.",
        )
    await cruds_phonebook.delete_groupement(groupement_id, db)
