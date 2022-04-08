from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_users
from app.schemas import schemas_core
from app.core.tags import Tags

router = APIRouter()


@router.get(
    "/users/",
    response_model=list[schemas_core.CoreUserSimple],
    status_code=200,
    tags=[Tags.users],
)
async def get_users(db: AsyncSession = Depends(get_db)):
    """Return all users from database as a list of dictionaries"""

    users = await cruds_users.get_users(db)
    return users


@router.post(
    "/users/",
    response_model=schemas_core.CoreUserSimple,
    status_code=201,
    tags=[Tags.users],
)
async def create_user(
    user: schemas_core.CoreUserCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new user in database and return it as a dictionary"""
    try:
        return await cruds_users.create_user(user=user, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/users/{user_id}",
    response_model=schemas_core.CoreUser,
    status_code=200,
    tags=[Tags.users],
)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Return user with id from database as a dictionary"""

    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete(
    "/users/{user_id}",
    status_code=204,
    tags=[Tags.users],
)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Delete user from database by id"""

    await cruds_users.delete_user(db=db, user_id=user_id)
