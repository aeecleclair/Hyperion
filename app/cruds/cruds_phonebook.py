from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pytz import timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_groups, cruds_users
from app.models import models_phonebook, models_core
from app.schemas import schemas_calendar
from app.utils.tools import fuzzy_search_user, get_file_from_data, save_file_as_data
from app.utils.types.phonebook_type import QueryType
from app.utils.types.tags import Tags
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.dependencies import get_db, get_request_id, get_settings, is_user_a_member_of

router = APIRouter()

# --------------------------------- Research --------------------------------- #
async def get_member_by_name(
    db: AsyncSession, query: str,) -> models_phonebook.Member | None:
    """Retrieve all the members corresponding to the query by their name/firstname/nickname from the database."""
    users = await cruds_users.get_users(db)
    return fuzzy_search_user(query, users)

async def get_member_by_role(db: AsyncSession, query: str)
    """Retrieve all the members corresponding to the query by their role"""
    return await db.execute(
        select(models_phonebook.Member).where(query in models_phonebook.Member.role)
    )
    

async def get_member_by_association(db: AsyncSession, query: str):
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

async def get_association_by_id(db: AsyncSession, id: str)-> models_phonebook.Association:
    return await db.execute(select(models_phonebook.Association).where(id == models_phonebook.Association.id))
    

async def edit_association_name(db: AsyncSession, id: str, newname: str):
    association = get_association_by_id(db, id)
    if association is None:
        raise HTTPException(status_code=404, detail="Association not found")
    
    await db.execute(update(models_phonebook.Association).where(id == models_phonebook.Association.id).values(name=newname))

async def delete_association(db: AsyncSession, id: str):
    association = get_association_by_id(db, id)
    if association is None:
        raise HTTPException(status_code=404, detail="Association not found")
    await db.execute(delete(models_phonebook.Association).where(id == models_phonebook.Association.id))
# ---------------------------------- Members --------------------------------- #

async def add_member(db: AsyncSession, member: models_phonebook.Member):
    db.add(member)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error
    
# ----------------------------------- Logos ---------------------------------- #
