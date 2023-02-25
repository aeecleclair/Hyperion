from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pytz import timezone
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.cruds import cruds_groups, cruds_users
from app.dependencies import get_db, get_request_id, get_settings, is_user_a_member_of
from app.models import models_core, models_phonebook
from app.schemas import schemas_calendar
from app.utils.tools import fuzzy_search_user, get_file_from_data, save_file_as_data
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.phonebook_type import QueryType
from app.utils.types.tags import Tags

router = APIRouter()


# --------------------------------- Research --------------------------------- #
async def get_member_by_name(
    db: AsyncSession,
    query: str,
) -> models_phonebook.Member | None:
    """Retrieve all the members corresponding to the query by their name/firstname/nickname from the database."""
    users = await cruds_users.get_users(db)
    return fuzzy_search_user(query, users)


async def get_member_by_role(
    db: AsyncSession, query: str
) -> models_phonebook.Member | None:
    """Retrieve all the members corresponding to the query by their role"""
    return await db.execute(
        select(models_phonebook.Member).where(query in models_phonebook.Member.role)
    )


async def get_member_by_association(
    db: AsyncSession, query: str
) -> models_member.Member | None:
    """Retrieve all the members corresponding to the query by their associations"""
    return await db.execute(
        select(models_phonebook.Member).where(
            query in models_phonebook.Member.association
        )
    )


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
) -> models_phonebook.Association:
    return await db.execute(
        select(models_phonebook.Association).where(
            id == models_phonebook.Association.id
        )
    )


async def edit_association(
    association_update: schema_phonebook.Association, db: AsyncSession, id: str
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


async def get_member_by_id(db: AsyncSession, id: str) -> models_phonebook.Member:
    return await db.execute(
        select(models_phonebook.Member).where(id == models_phonebook.Member.id)
    )


async def delete_member(db: AsyncSession, id: str):
    await db.execute(
        delete(models_phonebook.Member).where(id == models_phonebook.Member.id)
    )


async def edit_member(
    db: AsyncSession, member_update: schemas_phonebook.MemberUpdate, id: str
):
    await db.execute(
        update(models_phonebook.Member)
        .where(id == models_phonebook.Member.id)
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


async def get_role_by_id(db: AsyncSession) -> models_phonebook.Role:
    return await db.execute(select(models_phonebook.Role))


async def edit_role(
    role_update: schemas_phonebook.RoleUpdate, db: AsyncSession, id: str
):
    role = await get_role_by_id(db)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.execute(
        update(models_phonebook.Role)
        .where(models_phonebook.Role.id == id)
        .values(role_update)
    )


# ----------------------------------- Logos ---------------------------------- #
