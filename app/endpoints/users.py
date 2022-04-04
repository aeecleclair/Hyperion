from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_users
from app.schemas import schemas_users

router = APIRouter()

""" Requêtes fonctionnelles """


@router.get("/users/", response_model=list[schemas_users.CoreUserBase])
async def get_users(db: AsyncSession = Depends(get_db)):
    users = await cruds_users.get_users(db)
    return users


@router.post("/users/", response_model=schemas_users.CoreUserBase)
async def create_user(
    user: schemas_users.CoreUserCreate, db: AsyncSession = Depends(get_db)
):
    user_db = cruds_users.create_user(user=user, db=db)
    try:
        await db.commit()
        return user_db
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=422, detail="Email already registered")


@router.get("/users/{user_id}", response_model=schemas_users.CoreUser)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    await cruds_users.delete_user(db=db, user_id=user_id)
    return f"Utilisateur {user_id} supprimé !"


""" Requêtes foireuses """

# Changer l'endpoint car il pense que le /group est un user_id
@router.get("/users/groups", response_model=list[schemas_users.CoreGroupBase])
async def get_groups(db: AsyncSession = Depends(get_db)):
    groups = await cruds_users.get_groups(db)
    return groups


# @router.put("/users/{user_id}")
# async def edit_user(user_id):

#     return ""
