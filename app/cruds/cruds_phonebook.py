from fastapi import APIRouter
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_users
from app.models import models_phonebook
from app.schemas import schemas_phonebook
from app.utils.tools import fuzzy_search_user

router = APIRouter()


# --------------------------------- Research --------------------------------- #
async def get_member_by_name(
    db: AsyncSession,
    query: str,
) -> schemas_phonebook.RequestUserReturn | None:
    """Retrieve all the members corresponding to the query by their name/firstname/nickname from the database."""
    users = await cruds_users.get_users(db)
    found_users = fuzzy_search_user(query, users)
    temp = []
    for user in found_users:
        member_request = await db.execute(
            select(models_phonebook.Member).where(
                user.id == models_phonebook.Member.member_id
            )
        )
        member = member_request.scalars().first()

        associations_request = await db.execute(
            select(models_phonebook.Association).where(
                models_phonebook.Association.id == member.association_id
            )
        )
        associations = associations_request.scalars().all()

        roles_request = await db.execute(
            select(models_phonebook.Role).where(
                models_phonebook.Role.id == member.role_id
            )
        )
        roles = roles_request.scalars().all()

        temp.append(
            schemas_phonebook.UserReturn(
                user=member, associations=associations, roles=roles
            )
        )
    return schemas_phonebook.RequestUserReturn(response=temp)


async def get_member_by_role(
    db: AsyncSession, query: str
) -> list[schemas_phonebook.RequestUserReturn] | None:
    """Retrieve all the members corresponding to the query by their role"""
    role_id = db.execute(
        select(models_phonebook.Role.id).where(query in models_phonebook.Role.name)
    )
    result = await db.execute(
        select(models_phonebook.Member).where(
            models_phonebook.Member.role_id == role_id
        )
    )
    return result.scalars().all()


async def get_member_by_association(
    db: AsyncSession, query: str
) -> list[schemas_phonebook.RequestUserReturn] | None:
    """Retrieve all the members corresponding to the query by their associations"""
    association_id = db.execute(
        select(models_phonebook.Association.id).where(
            query in models_phonebook.Association.name
        )
    )
    result = await db.execute(
        select(models_phonebook.Member).where(
            association_id == models_phonebook.Member.association_id
        )
    )
    return result.scalars().all()


# ------------------------------- Associations ------------------------------- #


async def add_association(db: AsyncSession, association: models_phonebook.Association):
    db.add(association)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error


async def get_association_by_id(
    db: AsyncSession, id: str
) -> models_phonebook.Association | None:
    association_id = await db.execute(
        select(models_phonebook.Association).where(
            id == models_phonebook.Association.id
        )
    )
    return association_id.scalars().first()


async def edit_association(
    association_update: schemas_phonebook.AssociationEdit, db: AsyncSession, id: str
):
    await db.execute(
        update(models_phonebook.Association)
        .where(id == models_phonebook.Association.id)
        .values(association_update)
    )


async def delete_association(db: AsyncSession, id: str):
    await db.execute(
        delete(models_phonebook.Association).where(
            id == models_phonebook.Association.id
        )
    )


# ---------------------------------- Members --------------------------------- #


async def add_member(db: AsyncSession, member: models_phonebook.Member):
    db.add(member)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error


async def get_member_by_id(
    db: AsyncSession, member_id: str
) -> models_phonebook.Member | None:
    result = await db.execute(
        select(models_phonebook.Member).where(
            member_id == models_phonebook.Member.member_id
        )
    )
    return result.scalars().first()


async def delete_member(db: AsyncSession, member_id: str):
    await db.execute(
        delete(models_phonebook.Member).where(
            member_id == models_phonebook.Member.member_id
        )
    )


async def edit_member(
    db: AsyncSession,
    member_update: schemas_phonebook.AssociationMemberEdit,
    member_id: str,
):
    await db.execute(
        update(models_phonebook.Member)
        .where(member_id == models_phonebook.Member.member_id)
        .values(member_update)
    )
    await db.commit()


# ----------------------------------- Role ----------------------------------- #


async def create_role(db: AsyncSession, role: models_phonebook.Role):
    db.add(role)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error


async def delete_role(db: AsyncSession, id: str):
    await db.execute(
        delete(models_phonebook.Role).where(id == models_phonebook.Role.id)
    )


async def get_role_by_id(db: AsyncSession, role_id: str) -> str | None:
    role = await db.execute(select(models_phonebook.Role).where(role_id == id))
    return role.scalars().first()


async def edit_role(role_update: schemas_phonebook.RoleEdit, db: AsyncSession, id: str):
    await db.execute(
        update(models_phonebook.Role)
        .where(models_phonebook.Role.id == id)
        .values(role_update)
    )
