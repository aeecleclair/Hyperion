"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

School management is part of the core of Hyperion. These endpoints allow managing schools.
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.schools import cruds_schools, models_schools, schemas_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, schemas_users
from app.dependencies import (
    get_db,
    is_user_in,
)
from app.types.module import CoreModule

router = APIRouter(tags=["Schools"])

core_module = CoreModule(
    root="schools",
    tag="Schools",
    router=router,
)


@router.get(
    "/schools/",
    response_model=list[schemas_schools.CoreSchool],
    status_code=200,
)
async def read_schools(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all schools from database as a list of dictionaries
    """

    return await cruds_schools.get_schools(db)


@router.get(
    "/schools/{school_id}",
    response_model=schemas_schools.CoreSchool,
    status_code=200,
)
async def read_school(
    school_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return school with id from database as a dictionary.

    **This endpoint is only usable by administrators**
    """

    db_school = await cruds_schools.get_school_by_id(db=db, school_id=school_id)
    if db_school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return db_school


@router.post(
    "/schools/",
    response_model=schemas_schools.CoreSchool,
    status_code=201,
)
async def create_school(
    school: schemas_schools.CoreSchoolBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new school and add users to it based on the email regex.

    **This endpoint is only usable by administrators**
    """
    if (  # We can't have two schools with the same name
        await cruds_schools.get_school_by_name(school_name=school.name, db=db)
        is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=f"A school with the name {school.name} already exist",
        )

    try:
        db_school = models_schools.CoreSchool(
            id=uuid.uuid4(),
            name=school.name,
            email_regex=school.email_regex,
        )
        await cruds_schools.create_school(school=db_school, db=db)
        users = await cruds_users.get_users(
            db=db,
            schools_ids=[SchoolType.no_school.value],
        )
        for db_user in users:
            if re.match(db_school.email_regex, db_user.email):
                await cruds_users.update_user(
                    db,
                    db_user.id,
                    schemas_users.CoreUserUpdateAdmin(
                        school_id=db_school.id,
                        account_type=AccountType.other_school_student,
                    ),
                )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return db_school


@router.patch(
    "/schools/{school_id}",
    status_code=204,
)
async def update_school(
    school_id: uuid.UUID,
    school_update: schemas_schools.CoreSchoolUpdate,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update the name or the description of a school.

    **This endpoint is only usable by administrators**
    """
    school = await cruds_schools.get_school_by_id(db=db, school_id=school_id)

    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    # If the request ask to update the school name, we need to check it is available
    if school_update.name and school_update.name != school.name:
        if (
            await cruds_schools.get_school_by_name(
                school_name=school_update.name,
                db=db,
            )
            is not None
        ):
            raise HTTPException(
                status_code=400,
                detail=f"A school with the name {school.name} already exist",
            )
    await cruds_schools.update_school(
        db=db,
        school_id=school_id,
        school_update=school_update,
    )
    if (
        school_update.email_regex is not None
        and school_update.email_regex != school.email_regex
    ):
        await cruds_users.remove_users_from_school(db, school_id=school_id)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise
        users = await cruds_users.get_users(
            db,
            schools_ids=[SchoolType.no_school.value],
        )
        for db_user in users:
            if re.match(school_update.email_regex, db_user.email):
                await cruds_users.update_user(
                    db,
                    db_user.id,
                    schemas_users.CoreUserUpdateAdmin(
                        school_id=school.id,
                        account_type=AccountType.other_school_student,
                    ),
                )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise


@router.delete(
    "/schools/{school_id}",
    status_code=204,
)
async def delete_school(
    school_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete school from database.
    This will remove the school from all users but won't delete any user.

    `SchoolTypes` schools can not be deleted.

    **This endpoint is only usable by administrators**
    """

    if school_id in (SchoolType.list()):
        raise HTTPException(
            status_code=400,
            detail="SchoolTypes schools can not be deleted",
        )

    school = await cruds_schools.get_school_by_id(db=db, school_id=school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")

    await cruds_users.remove_users_from_school(db=db, school_id=school_id)

    await cruds_schools.delete_school(db=db, school_id=school_id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
