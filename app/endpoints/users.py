from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_users
from app.schemas import schemas_core

router = APIRouter()

""" Requêtes fonctionnelles """


@router.get("/users/", response_model=list[schemas_core.CoreUserBase])
async def get_users(db: AsyncSession = Depends(get_db)):
    users = await cruds_users.get_users(db)
    return users


@router.post("/users/", response_model=schemas_core.CoreUserBase)
async def create_user(
    user: schemas_core.CoreUserCreate, db: AsyncSession = Depends(get_db)
):
    try:
        return await cruds_users.create_user(user=user, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/users/{user_id}", response_model=schemas_core.CoreUser)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    await cruds_users.delete_user(db=db, user_id=user_id)
    return f"Utilisateur {user_id} supprimé !"


# @router.put("/users/{user_id}")
# async def edit_user(user_id):

#     return ""
