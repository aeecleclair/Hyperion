"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

School management is part of the core of Hyperion. These endpoints allow managing schools.
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.groups.groups_type import AccountType, GroupType
from app.core.schools import cruds_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    is_user_an_ecl_member,
    is_user_in,
)

router = APIRouter(tags=["Schools"])


@router.get(
    "/schools/",
    response_model=list[schemas_core.CoreSchoolSimple],
    status_code=200,
)
async def read_schools(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_an_ecl_member),
):
    """
    Return all schools from database as a list of dictionaries
    """

    schools = await cruds_schools.get_schools(db)
    return schools


@router.get(
    "/schools/{school_id}",
    response_model=schemas_core.CoreSchool,
    status_code=200,
)
async def read_school(
    school_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Return school with id from database as a dictionary. This includes a list of users being members of the school.

    **This endpoint is only usable by administrators**
    """

    db_school = await cruds_schools.get_school_by_id(db=db, school_id=school_id)
    if db_school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return db_school


@router.post(
    "/schools/",
    response_model=schemas_core.CoreSchoolSimple,
    status_code=201,
)
async def create_school(
    school: schemas_core.CoreSchoolBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new school.

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
        db_school = models_core.CoreSchool(
            id=str(uuid.uuid4()),
            name=school.name,
            email_regex=school.email_regex,
        )
        await cruds_schools.create_school(school=db_school, db=db)
        users = await cruds_users.get_users(
            db=db,
            included_account_types=[AccountType.external],
        )
        for db_user in users:
            if re.match(db_school.email_regex, db_user.email):
                await cruds_users.update_user(
                    db,
                    db_user.id,
                    schemas_core.CoreUserUpdateAdmin(
                        school_id=db_school.id,
                        account_type=AccountType.other_school_student,
                    ),
                )
        await db.commit()
    except ValueError as error:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="School creation failed due to database integrity error",
        )
    else:
        return db_school


@router.patch(
    "/schools/{school_id}",
    status_code=204,
)
async def update_school(
    school_id: str,
    school_update: schemas_core.CoreSchoolUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
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
        users = await cruds_users.get_users(db, schools_ids=[SchoolType.no_school])
        for db_user in users:
            if re.match(school_update.email_regex, db_user.email):
                await cruds_users.update_user(
                    db,
                    db_user.id,
                    schemas_core.CoreUserUpdateAdmin(
                        school_id=school.id,
                        account_type=AccountType.other_school_student,
                    ),
                )
            await db.commit()


@router.delete(
    "/schools/{school_id}",
    status_code=204,
)
async def delete_school(
    school_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Delete school from database.
    This will remove the school from all users but won't delete any user.

    `SchoolTypes` schools can not be deleted.

    **This endpoint is only usable by administrators**
    """

    if school_id in (item.value for item in SchoolType):
        raise HTTPException(
            status_code=400,
            detail="SchoolTypes schools can not be deleted",
        )

    school = await cruds_schools.get_school_by_id(db=db, school_id=school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")

    users = await cruds_users.get_users(db=db, schools_ids=[school_id])
    for db_user in users:
        await cruds_users.update_user(
            db,
            db_user.id,
            schemas_core.CoreUserUpdateAdmin(
                school_id=SchoolType.no_school.value,
                account_type=AccountType.external,
            ),
        )

    await cruds_schools.delete_school(db=db, school_id=school_id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="School deletion failed due to database integrity error",
        )
